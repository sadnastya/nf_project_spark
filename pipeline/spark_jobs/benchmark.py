import time

from pyspark.sql import functions as F

from pipeline import settings
from pipeline.spark_jobs.common import (_fs, core_path, hdfs_du, mart_path, read_json_hdfs,
                                        spark_session, write_json_hdfs)
from pipeline.spark_jobs.raw_to_core import build_dim_account, build_dim_terminal, typed_transactions

REPEAT = 2


def timed(action, repeat=REPEAT):
    best, result = None, None
    for _ in range(repeat):
        t = time.perf_counter()
        result = action()
        dt = time.perf_counter() - t
        best = dt if best is None else min(best, dt)
    return round(best, 2), result


def list_batches(spark):
    jvm, fs = _fs(spark)
    root = jvm.org.apache.hadoop.fs.Path(settings.META_ROOT)
    return sorted(s.getPath().getName().split("=")[1] for s in fs.listStatus(root)
                  if s.getPath().getName().startswith("batch="))


def main():
    spark = spark_session("benchmark")
    spark.sparkContext.setLogLevel("WARN")
    batches = list_batches(spark)
    last = batches[-1]
    res = {"batches": batches}

    # объёмы по слоям
    manifests = [read_json_hdfs(spark, f"{settings.META_ROOT}/batch={b}/load_manifest.json") for b in batches]
    files = [f for m in manifests for f in m["files"]]
    tx = [f for f in files if f["table"] == "transactions"]
    res["storage"] = {
        "landing_csv_total": sum(f["raw_bytes"] for f in files),
        "landing_csv_transactions": sum(f["raw_bytes"] for f in tx),
        "raw_gz_total": hdfs_du(spark, settings.RAW_ROOT),
        "raw_gz_transactions": sum(f["gz_bytes"] for f in tx),
        "core_fact": hdfs_du(spark, f"{settings.CORE_ROOT}/fact_transactions"),
        "core_dims": sum(hdfs_du(spark, f"{settings.CORE_ROOT}/{d}") for d in ("dim_terminal", "dim_client", "dim_account")),
        "marts": hdfs_du(spark, settings.MART_ROOT),
        "transactions_rows_raw": sum(f["rows"] for f in tx),
        "fact_rows": spark.read.parquet(core_path("fact_transactions")).count(),
    }

    # кодеки и форматы на одном месяце факта
    month = spark.read.parquet(core_path("fact_transactions")).filter(F.col("txn_month") == last).drop("txn_month")
    month = month.persist()
    month.count()
    day = f"{last}-15"
    codecs = {}
    variants = [("csv", "none"), ("csv", "gzip"), ("parquet", "none"), ("parquet", "snappy"),
                ("parquet", "gzip"), ("parquet", "zstd")]
    for fmt, codec in variants:
        path = settings.hdfs_url(f"{settings.DATALAKE_ROOT}/_bench/{fmt}_{codec}")
        w = month.repartition(2).sortWithinPartitions("txn_ts").write.mode("overwrite").option("compression", codec)
        t = time.perf_counter()
        (w.option("header", True).csv(path) if fmt == "csv" else w.parquet(path))
        write_s = round(time.perf_counter() - t, 2)
        if fmt == "csv":
            df = spark.read.option("header", True).schema(month.schema).csv(path)
        else:
            df = spark.read.parquet(path)
        scan_s, _ = timed(lambda: df.agg(F.sum("amount")).collect())
        point_s, _ = timed(lambda: df.filter(F.col("txn_date") == day).agg(F.count(F.lit(1))).collect())
        codecs[f"{fmt}/{codec}"] = {"bytes": hdfs_du(spark, path.replace(settings.HDFS_URI, "")),
                                    "write_s": write_s, "sum_amount_s": scan_s, "one_day_count_s": point_s}
    month.unpersist()
    jvm, fs = _fs(spark)
    fs.delete(jvm.org.apache.hadoop.fs.Path(f"{settings.DATALAKE_ROOT}/_bench"), True)
    res["codecs_one_month"] = {"month": last, **codecs}

    # одни и те же запросы над raw / core / marts
    q = {}
    # raw: каждый раз парсим CSV.gz, типизируем, строим справочник терминалов
    raw_tx = typed_transactions(spark, "*")
    raw_term = build_dim_terminal(spark, last)
    raw_acc = build_dim_account(spark, last)
    fact = spark.read.parquet(core_path("fact_transactions"))
    term = spark.read.parquet(core_path("dim_terminal"))
    dm_daily = spark.read.parquet(mart_path("dm_daily_sales"))
    dm_client = spark.read.parquet(mart_path("dm_client_monthly"))
    purchase = (F.col("status") == "success") & (F.col("amount") > 0)

    # Q1: оборот по месяцам, ритейлерам и регионам за весь период
    q1_raw = lambda: (raw_tx.filter(purchase)
                      .join(F.broadcast(raw_term.select("source_bank", "terminal_id", "retailer", "region")),
                            ["source_bank", "terminal_id"])
                      .groupBy(F.date_format("txn_ts", "yyyy-MM").alias("m"), "retailer", "region")
                      .agg(F.sum("amount")).collect())
    q1_core = lambda: (fact.filter(purchase)
                       .join(F.broadcast(term.select("terminal_key", "retailer", "region")), "terminal_key")
                       .groupBy("txn_month", "retailer", "region").agg(F.sum("amount")).collect())
    q1_mart = lambda: (dm_daily.groupBy("txn_month", "retailer", "region").agg(F.sum("turnover")).collect())

    # Q2: почасовые продажи X5 в Москве за один день
    q2_filter_raw = F.to_date("txn_ts") == F.lit(day).cast("date")
    q2_raw = lambda: (raw_tx.filter(purchase & q2_filter_raw)
                      .join(F.broadcast(raw_term.filter("retailer = 'X5 Group' and region = 'Москва'")
                                        .select("source_bank", "terminal_id")), ["source_bank", "terminal_id"])
                      .groupBy(F.hour("txn_ts")).agg(F.sum("amount"), F.count(F.lit(1))).collect())
    q2_core = lambda: (fact.filter((F.col("txn_month") == last) & (F.col("txn_date") == day) & purchase)
                       .join(F.broadcast(term.filter("retailer = 'X5 Group' and region = 'Москва'")
                                         .select("terminal_key")), "terminal_key")
                       .groupBy("txn_hour").agg(F.sum("amount"), F.count(F.lit(1))).collect())

    # Q3: топ-10 клиентов по обороту за весь период
    q3_raw = lambda: (raw_tx.filter(purchase)
                      .join(F.broadcast(raw_acc.select("source_bank", "account_id", "client_key")),
                            ["source_bank", "account_id"])
                      .groupBy("client_key").agg(F.sum("amount").alias("s")).orderBy(F.desc("s")).limit(10).collect())
    q3_core = lambda: (fact.filter(purchase).groupBy("client_key").agg(F.sum("amount").alias("s"))
                       .orderBy(F.desc("s")).limit(10).collect())
    q3_mart = lambda: (dm_client.groupBy("client_key").agg(F.sum("turnover").alias("s"))
                       .orderBy(F.desc("s")).limit(10).collect())

    for name, variants_ in {
        "Q1_turnover_by_month_retailer_region": {"raw_csv_gz": q1_raw, "core_parquet": q1_core, "mart": q1_mart},
        "Q2_hourly_x5_moscow_one_day": {"raw_csv_gz": q2_raw, "core_parquet": q2_core},
        "Q3_top10_clients_year": {"raw_csv_gz": q3_raw, "core_parquet": q3_core, "mart": q3_mart},
    }.items():
        q[name] = {}
        for layer, fn in variants_.items():
            q[name][layer], _ = timed(fn, repeat=1 if layer == "raw_csv_gz" else REPEAT)
            print(f"[bench] {name} {layer}: {q[name][layer]} s")
    res["queries_seconds"] = q

    write_json_hdfs(spark, f"{settings.META_ROOT}/benchmark.json", res)
    print("[bench]", res)
    spark.stop()


if __name__ == "__main__":
    main()
