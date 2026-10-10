import argparse
import time

from pyspark.sql import Window
from pyspark.sql import functions as F

from pipeline import settings
from pipeline.spark_jobs.common import core_path, mart_path, spark_session, write_json_hdfs

def is_purchase():
    return (F.col("status") == "success") & ~F.col("is_refund")


def write_mart(df, name):
    (df.repartition(1).write.mode("overwrite").partitionBy("txn_month").parquet(mart_path(name)))


def run(batch: str) -> dict:
    spark = spark_session(f"core_to_marts_{batch}")
    t0 = time.time()
    fact = spark.read.parquet(core_path("fact_transactions")).filter(F.col("txn_month") == batch)
    terminal = spark.read.parquet(core_path("dim_terminal")).select(
        "terminal_key", "retailer", F.coalesce("region", F.lit("н/д")).alias("region"),
        "channel", "store_id", "store_format", "checkout_type")
    client = spark.read.parquet(core_path("dim_client")).select("client_key", "gender", "age_group")

    f = fact.join(F.broadcast(terminal), "terminal_key").withColumn("purchase", is_purchase()).persist()
    turnover = F.sum(F.when(F.col("purchase"), F.col("amount")))
    purchases = F.sum(F.col("purchase").cast("int"))

    daily = (f.groupBy("txn_month", "txn_date", "source_bank", "retailer", "region", "channel")
             .agg(purchases.alias("purchases_cnt"),
                  F.coalesce(turnover, F.lit(0)).cast("decimal(18,2)").alias("turnover"),
                  F.coalesce(F.sum(F.when(F.col("is_refund") & (F.col("status") == "success"), -F.col("amount"))),
                             F.lit(0)).cast("decimal(18,2)").alias("refunds_amount"),
                  F.sum((F.col("status") == "failed").cast("int")).alias("failed_cnt"),
                  F.count(F.lit(1)).alias("attempts_cnt"),
                  F.countDistinct(F.when(F.col("purchase"), F.col("client_key"))).alias("unique_clients"))
             .withColumn("avg_check", (F.col("turnover") / F.col("purchases_cnt")).cast("decimal(14,2)")))
    write_mart(daily, "dm_daily_sales")

    p = f.filter("purchase")
    retailer = (p.groupBy("txn_month", "retailer", "store_format", "checkout_type")
                .agg(F.count(F.lit(1)).alias("purchases_cnt"),
                     F.sum("amount").cast("decimal(18,2)").alias("turnover"),
                     F.countDistinct("client_key").alias("unique_clients"),
                     F.countDistinct("terminal_key").alias("active_terminals"),
                     F.countDistinct("store_id").alias("active_stores"))
                .withColumn("avg_check", (F.col("turnover") / F.col("purchases_cnt")).cast("decimal(14,2)"))
                .withColumn("turnover_per_terminal",
                            (F.col("turnover") / F.col("active_terminals")).cast("decimal(18,2)")))
    write_mart(retailer, "dm_retailer_monthly")

    by_ret = p.groupBy("client_key", "retailer").agg(F.sum("amount").alias("ret_turnover"))
    top = (by_ret.withColumn("rn", F.row_number().over(
        Window.partitionBy("client_key").orderBy(F.desc("ret_turnover"), "retailer")))
        .filter("rn = 1").select("client_key", F.col("retailer").alias("top_retailer")))
    clients = (p.groupBy("txn_month", "client_key", "source_bank")
               .agg(F.count(F.lit(1)).alias("purchases_cnt"),
                    F.sum("amount").cast("decimal(18,2)").alias("turnover"),
                    F.countDistinct("txn_date").alias("active_days"),
                    F.countDistinct("retailer").alias("retailers_cnt"),
                    F.max("txn_ts").alias("last_purchase_ts"))
               .withColumn("avg_check", (F.col("turnover") / F.col("purchases_cnt")).cast("decimal(14,2)"))
               .join(top, "client_key", "left")
               .join(F.broadcast(client), "client_key", "left"))
    write_mart(clients, "dm_client_monthly")

    iso_dow = ((F.dayofweek("txn_date") + 5) % 7 + 1).cast("tinyint")  # 1=пн .. 7=вс
    hourly = (f.groupBy("txn_month", "retailer", "channel", iso_dow.alias("day_of_week"), "txn_hour")
              .agg(F.count(F.lit(1)).alias("attempts_cnt"),
                   purchases.alias("purchases_cnt"),
                   F.avg(F.when(F.col("purchase"), F.col("amount"))).cast("decimal(14,2)").alias("avg_amount"),
                   (F.sum((F.col("status") == "failed").cast("int")) / F.count(F.lit(1))).alias("failed_share"),
                   F.countDistinct("txn_date").alias("days_cnt")))
    write_mart(hourly, "dm_hourly_load")

    # сверка витрины с фактом (проверяется DQ-задачей в Airflow)
    fact_sum = p.agg(F.count(F.lit(1)).alias("cnt"), F.sum("amount").alias("sum")).first()
    mart_sum = (spark.read.parquet(mart_path("dm_daily_sales")).filter(F.col("txn_month") == batch)
                .agg(F.sum("purchases_cnt").alias("cnt"), F.sum("turnover").alias("sum")).first())
    metrics = {
        "batch": batch,
        "fact_purchases": fact_sum["cnt"], "fact_turnover": str(fact_sum["sum"]),
        "mart_purchases": mart_sum["cnt"], "mart_turnover": str(mart_sum["sum"]),
        "rows": {name: spark.read.parquet(mart_path(name)).filter(F.col("txn_month") == batch).count()
                 for name in ("dm_daily_sales", "dm_retailer_monthly", "dm_client_monthly", "dm_hourly_load")},
        "seconds": round(time.time() - t0, 1),
    }
    write_json_hdfs(spark, f"{settings.META_ROOT}/batch={batch}/marts_metrics.json", metrics)
    print("[marts]", metrics)
    spark.stop()
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    run(ap.parse_args().batch)
