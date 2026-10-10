import json
import os
import socket

from pyspark.sql import Column, SparkSession
from pyspark.sql import functions as F

from pipeline import settings

KEY_BASE = 1_000_000_000  # суррогатный ключ = номер_банка * 1e9 + id в источнике


def spark_session(app: str, master: str = None, conf: dict = None) -> SparkSession:
    builder = SparkSession.builder.appName(app)
    if master or os.getenv("SPARK_MASTER"):
        builder = builder.master(master or os.getenv("SPARK_MASTER"))
    builder = (builder
            # драйвер работает в контейнере Airflow/Jupyter (client mode): исполнители
            # должны достучаться до него по IP контейнера
            .config("spark.driver.host", socket.gethostbyname(socket.gethostname()))
            .config("spark.driver.bindAddress", "0.0.0.0")
            .config("spark.hadoop.fs.defaultFS", settings.HDFS_URI)
            .config("spark.hadoop.dfs.replication", os.getenv("HDFS_REPLICATION", "1"))  # одна datanode
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
            .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
            .config("spark.sql.parquet.compression.codec", "zstd")
            .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "16"))
            .config("spark.sql.adaptive.enabled", "true"))
    for k, v in (conf or {}).items():
        builder = builder.config(k, v)
    return builder.getOrCreate()


def surrogate_key(bank_col: Column, id_col: Column) -> Column:
    """Детерминированный ключ: не нужен lookup, ключи стабильны между перезапусками батчей."""
    return (F.when(bank_col == "bank1", F.lit(1)).otherwise(F.lit(2)).cast("long") * KEY_BASE
            + id_col.cast("long"))


def raw_path(source: str, table: str, batch: str = "*") -> str:
    return settings.hdfs_url(f"{settings.RAW_ROOT}/{source}/{table}/batch={batch}")


def read_raw(spark: SparkSession, source: str, table: str, batch: str):
    """Сырой CSV.gz: всё читается строками, типизация — явная, в transform (без inferSchema)."""
    return (spark.read
            .option("header", True)
            .option("sep", settings.SOURCES[source]["sep"])
            .option("quote", '"').option("escape", '"')
            .option("mode", "PERMISSIVE")
            .csv(raw_path(source, table, batch)))


def core_path(name: str) -> str:
    return settings.hdfs_url(f"{settings.CORE_ROOT}/{name}")


def mart_path(name: str) -> str:
    return settings.hdfs_url(f"{settings.MART_ROOT}/{name}")


def _fs(spark: SparkSession):
    jvm = spark.sparkContext._jvm
    conf = spark.sparkContext._jsc.hadoopConfiguration()
    return jvm, jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(settings.HDFS_URI), conf)


def write_json_hdfs(spark: SparkSession, path: str, obj) -> None:
    jvm, fs = _fs(spark)
    out = fs.create(jvm.org.apache.hadoop.fs.Path(path), True)
    out.write(bytearray(json.dumps(obj, ensure_ascii=False, indent=1, default=str), "utf-8"))
    out.close()


def read_json_hdfs(spark: SparkSession, path: str):
    jvm, fs = _fs(spark)
    p = jvm.org.apache.hadoop.fs.Path(path)
    if not fs.exists(p):
        return None
    stream = fs.open(p)
    reader = jvm.java.io.BufferedReader(jvm.java.io.InputStreamReader(stream, "UTF-8"))
    lines = []
    while (line := reader.readLine()) is not None:
        lines.append(line)
    reader.close()
    return json.loads("\n".join(lines))


def hdfs_du(spark: SparkSession, path: str) -> int:
    """Размер каталога в HDFS (байты, без учёта репликации)."""
    jvm, fs = _fs(spark)
    p = jvm.org.apache.hadoop.fs.Path(path)
    return fs.getContentSummary(p).getLength() if fs.exists(p) else 0
