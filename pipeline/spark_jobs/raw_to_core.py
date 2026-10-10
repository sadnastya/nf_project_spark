import argparse
import time
from datetime import date
import calendar

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from pipeline import settings
from pipeline.spark_jobs.common import (core_path, read_raw, spark_session, surrogate_key,
                                        write_json_hdfs)

AMOUNT_TYPE = "decimal(14,2)"
TS_FORMAT = {"bank1": "yyyy-MM-dd HH:mm:ss", "bank2": "dd.MM.yyyy HH:mm:ss"}
TXN_STATUS = {"successful": "success", "success": "success", "pending": "pending",
              "processing": "pending", "rejected": "failed", "failed": "failed"}
ACC_STATUS = {"active": "active", "open": "active", "inactive": "inactive", "pending": "inactive",
              "closed": "closed", "frozen": "frozen"}
FACT_FILES_PER_MONTH = 2
PARQUET_BLOCK_SIZE = 8 * 2**20  # несколько row group'ов на файл -> работает data skipping


def mapping(d: dict):
    return F.create_map(*[F.lit(x) for kv in d.items() for x in kv])


def normalize_region(c):
    c = F.trim(c)
    c = F.regexp_replace(c, "кray", "край")          # латиница в выгрузке Магнита
    c = F.regexp_replace(c, " обл\\.$", " область")  # «обл.» -> «область»
    return c


# измерения
def build_dim_terminal(spark: SparkSession, batch: str) -> DataFrame:
    # X5: адрес уже разложен по колонкам
    t, tt = read_raw(spark, "x5", "terminals", batch).alias("t"), read_raw(spark, "x5", "terminal_types", batch).alias("tt")
    s, st = read_raw(spark, "x5", "stores", batch).alias("s"), read_raw(spark, "x5", "store_types", batch).alias("st")
    x5 = (t.join(tt, F.col("t.terminal_type") == F.col("tt.id"))
          .join(s, F.col("t.store_id") == F.col("s.id"))
          .join(st, F.col("s.store_type") == F.col("st.id"))
          .select(F.lit("X5 Group").alias("retailer"),
                  F.col("s.id").cast("int").alias("store_id"),
                  F.col("st.type").alias("store_format"),
                  F.lower("tt.type").alias("checkout_type"),
                  normalize_region(F.col("s.region")).alias("region"),
                  F.trim("s.city").alias("city"),
                  F.trim("s.address").alias("address"),
                  F.col("t.acquirer_bank"),
                  F.col("t.acquirer_terminal_id").cast("int").alias("acquirer_terminal_id")))

    # Магнит: full_address = "Регион, г. Город, ул. Улица, д. N"
    mt, ms = read_raw(spark, "magnit", "terminals", batch).alias("mt"), read_raw(spark, "magnit", "stores", batch)
    mst = read_raw(spark, "magnit", "stores_type", batch).alias("mst")
    parts = F.split(F.col("full_address"), ",\\s*")
    ms = ms.select(F.col("id"), F.col("store_type"),
                   normalize_region(parts.getItem(0)).alias("region"),
                   F.regexp_replace(parts.getItem(1), "^г\\.\\s*", "").alias("city"),
                   F.concat_ws(" ", parts.getItem(2),
                               F.regexp_replace(parts.getItem(3), "^д\\.\\s*", "")).alias("address")).alias("ms")
    magnit = (mt.join(ms, F.col("mt.address") == F.col("ms.id"))
              .join(mst, F.col("ms.store_type") == F.col("mst.id"))
              .select(F.lit("Магнит").alias("retailer"),
                      F.col("ms.id").cast("int").alias("store_id"),
                      F.col("mst.type").alias("store_format"),
                      F.lower("mt.terminal_type").alias("checkout_type"),
                      "ms.region", "ms.city", "ms.address",
                      F.col("mt.acquirer_bank"),
                      F.col("mt.acquirer_terminal_id").cast("int").alias("acquirer_terminal_id")))
    retail = x5.unionByName(magnit).alias("r")

    # терминалы банков
    def bank_terminals(bank, merchant_table, merchant_fk, with_status):
        bt = read_raw(spark, bank, "terminals", batch).alias("bt")
        btt = read_raw(spark, bank, "terminal_type", batch).alias("btt")
        m = read_raw(spark, bank, merchant_table, batch).alias("m")
        df = (bt.join(btt, F.col("bt.type") == F.col("btt.id"), "left")
              .join(m, F.col(f"bt.{merchant_fk}") == F.col("m.id"), "left"))
        if with_status:
            bts = read_raw(spark, bank, "terminal_status", batch).alias("bts")
            df = df.join(bts, F.col("bt.status") == F.col("bts.id"), "left")
            status = F.col("bts.status")
        else:
            status = F.lit("active")  # в bank2 нет статуса терминала
        return df.select(F.lit(bank).alias("source_bank"),
                         F.col("bt.id").cast("int").alias("terminal_id"),
                         F.col("btt.type").alias("bank_terminal_type"),
                         status.alias("terminal_status"),
                         F.col("m.name").alias("merchant_name"),
                         F.col("m.inn").alias("merchant_inn"),
                         F.to_date("bt.created_at").alias("installed_at"))

    banks = (bank_terminals("bank1", "merchants", "merchant_id", True)
             .unionByName(bank_terminals("bank2", "sellers", "seller_id", False))).alias("b")

    dim = banks.join(retail, (F.col("b.source_bank") == F.col("r.acquirer_bank"))
                     & (F.col("b.terminal_id") == F.col("r.acquirer_terminal_id")), "left")
    channel = (F.when(F.col("bank_terminal_type") == "online", "online")
               .when((F.col("bank_terminal_type") == "self-service")
                     | (F.col("checkout_type") == "самообслуживание"), "self_service")
               .otherwise("pos"))
    return dim.select(
        surrogate_key(F.col("b.source_bank"), F.col("b.terminal_id")).alias("terminal_key"),
        "b.source_bank", "b.terminal_id", channel.alias("channel"), "terminal_status",
        "merchant_name", "merchant_inn",
        F.coalesce("retailer", F.lit("Прочие")).alias("retailer"),
        "store_id", "store_format", "checkout_type", "region", "city", "address", "installed_at")


def build_dim_client(spark: SparkSession, batch: str) -> DataFrame:
    y, m = map(int, batch.split("-"))
    as_of = F.lit(date(y, m, calendar.monthrange(y, m)[1]))
    dfs = [read_raw(spark, bank, "clients", batch).select(
        F.lit(bank).alias("source_bank"), F.col("id").cast("int").alias("client_id"),
        F.upper("gender").alias("gender"), F.to_date("date_of_birth").alias("birth_date"))
        for bank in settings.BANKS]
    df = dfs[0].unionByName(dfs[1])
    age = F.floor(F.months_between(as_of, "birth_date") / 12).cast("int")
    age_group = (F.when(age < 25, "18-24").when(age < 35, "25-34").when(age < 45, "35-44")
                 .when(age < 55, "45-54").otherwise("55+"))
    return df.select(surrogate_key(F.col("source_bank"), F.col("client_id")).alias("client_key"),
                     "source_bank", "client_id", "gender", "birth_date",
                     age.alias("age"), age_group.alias("age_group"))


def build_dim_account(spark: SparkSession, batch: str) -> DataFrame:
    dfs = []
    for bank in settings.BANKS:
        a = read_raw(spark, bank, "accounts", batch).alias("a")
        at = read_raw(spark, bank, "account_type", batch).alias("at")
        ast = read_raw(spark, bank, "account_status", batch).alias("ast")
        dfs.append(a.join(at, F.col("a.type") == F.col("at.id"), "left")
                   .join(ast, F.col("a.status") == F.col("ast.id"), "left")
                   .select(F.lit(bank).alias("source_bank"),
                           F.col("a.id").cast("int").alias("account_id"),
                           F.col("a.client_id").cast("int").alias("client_id"),
                           F.col("at.type").alias("account_type"),
                           mapping(ACC_STATUS)[F.col("ast.status")].alias("account_status"),
                           F.col("a.currency"),
                           F.col("a.balance").cast("decimal(18,2)").alias("balance")))
    df = dfs[0].unionByName(dfs[1])
    return df.select(surrogate_key(F.col("source_bank"), F.col("account_id")).alias("account_key"),
                     surrogate_key(F.col("source_bank"), F.col("client_id")).alias("client_key"),
                     "source_bank", "account_id", "account_type", "account_status", "currency", "balance")


# факт
def typed_transactions(spark: SparkSession, batch: str) -> DataFrame:
    """Сырые транзакции обоих банков в едином типизированном виде (до очистки)."""
    dfs = []
    for bank in settings.BANKS:
        tx = read_raw(spark, bank, "transactions", batch)
        st = read_raw(spark, bank, "transaction_status", batch).select(
            F.col("id").alias("status_id"), mapping(TXN_STATUS)[F.col("status")].alias("status"))
        amount = F.col("amount")
        if bank == "bank2":
            amount = F.regexp_replace(amount, ",", ".")
        dfs.append(tx.join(F.broadcast(st), tx["status"] == st["status_id"], "left").select(
            F.lit(bank).alias("source_bank"),
            F.col("id").cast("long").alias("txn_id"),
            F.col("terminal_id").cast("int").alias("terminal_id"),
            F.col("account_id").cast("int").alias("account_id"),
            F.to_timestamp("transaction_date", TS_FORMAT[bank]).alias("txn_ts"),
            amount.cast(AMOUNT_TYPE).alias("amount"),
            F.col("currency"),
            st["status"].alias("status"),
            F.col("transaction_date").alias("raw_transaction_date"),
            F.col("amount").alias("raw_amount")))
    return dfs[0].unionByName(dfs[1])


def run(batch: str) -> dict:
    spark = spark_session(f"raw_to_core_{batch}")
    t0 = time.time()
    metrics = {"batch": batch}

    # измерения: полный снимок источника -> перезапись (SCD1); ключи детерминированы,
    # поэтому ранее записанные партиции факта остаются согласованными с новыми измерениями
    dims = {"dim_terminal": build_dim_terminal(spark, batch),
            "dim_client": build_dim_client(spark, batch),
            "dim_account": build_dim_account(spark, batch)}
    metrics["dims"] = {}
    for name, df in dims.items():
        df.repartition(1).write.mode("overwrite").parquet(core_path(name))
        metrics["dims"][name] = spark.read.parquet(core_path(name)).count()
    dim_terminal = spark.read.parquet(core_path("dim_terminal"))
    dim_account = spark.read.parquet(core_path("dim_account"))
    metrics["terminals_linked_to_store"] = dim_terminal.filter("store_id is not null").count()

    tx = typed_transactions(spark, batch).persist()
    metrics["raw_rows"] = {r["source_bank"]: r["count"] for r in tx.groupBy("source_bank").count().collect()}

    deduped = tx.dropDuplicates(["source_bank", "txn_id"])
    deduped_rows = {r["source_bank"]: r["count"] for r in deduped.groupBy("source_bank").count().collect()}
    metrics["duplicates"] = {b: metrics["raw_rows"][b] - deduped_rows.get(b, 0) for b in metrics["raw_rows"]}

    term = F.broadcast(dim_terminal.select("terminal_key", "source_bank", "terminal_id"))
    acc = F.broadcast(dim_account.select("account_key", "client_key", "source_bank", "account_id"))
    joined = deduped.join(term, ["source_bank", "terminal_id"], "left").join(acc, ["source_bank", "account_id"], "left")
    reason = (F.when(F.col("txn_id").isNull(), "bad_id")
              .when(F.col("txn_ts").isNull(), "bad_timestamp")
              .when(F.col("amount").isNull(), "bad_amount")
              .when(F.date_format("txn_ts", "yyyy-MM") != batch, "out_of_batch_period")
              .when(F.col("terminal_key").isNull(), "unknown_terminal")
              .when(F.col("account_key").isNull(), "unknown_account")
              .when(F.col("status").isNull(), "unknown_status"))
    validated = joined.withColumn("reject_reason", reason).persist()

    rejected = validated.filter(F.col("reject_reason").isNotNull())
    (rejected.select("source_bank", "txn_id", "terminal_id", "account_id", "raw_transaction_date",
                     "raw_amount", "status", "reject_reason")
     .repartition(1).write.mode("overwrite")
     .parquet(settings.hdfs_url(f"{settings.QUARANTINE_ROOT}/transactions/batch={batch}")))
    metrics["rejected"] = {r["reject_reason"]: r["count"]
                           for r in rejected.groupBy("reject_reason").count().collect()}

    fact = (validated.filter(F.col("reject_reason").isNull())
            .select("txn_id", "source_bank", "txn_ts",
                    F.to_date("txn_ts").alias("txn_date"),
                    F.hour("txn_ts").cast("tinyint").alias("txn_hour"),
                    "terminal_key", "account_key", "client_key", "amount", "currency", "status",
                    (F.col("amount") < 0).alias("is_refund"),
                    F.lit(batch).alias("txn_month")))
    (fact.repartitionByRange(FACT_FILES_PER_MONTH, "txn_ts")
     .sortWithinPartitions("txn_ts")
     .write.mode("overwrite")                       # dynamic: перезаписывается только txn_month=batch
     .option("parquet.block.size", PARQUET_BLOCK_SIZE)
     .partitionBy("txn_month")
     .parquet(core_path("fact_transactions")))
    metrics["fact_rows"] = (spark.read.parquet(core_path("fact_transactions"))
                            .filter(F.col("txn_month") == batch).count())

    metrics["seconds"] = round(time.time() - t0, 1)
    write_json_hdfs(spark, f"{settings.META_ROOT}/batch={batch}/core_metrics.json", metrics)
    print("[core]", metrics)
    spark.stop()
    return metrics


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--batch", required=True)
    run(p.parse_args().batch)
