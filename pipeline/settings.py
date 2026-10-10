import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Локальная landing-зона: сюда extract-слой «кладёт файлы на диск».
LANDING_DIR = Path(os.getenv("LANDING_DIR", REPO_ROOT / "data" / "landing"))
# Справочники ритейлеров из работы №1 — используются как seed для генератора.
SEED_DIR = Path(os.getenv("SEED_DIR", REPO_ROOT / "data_stores"))

WEBHDFS_URL = os.getenv("WEBHDFS_URL", "http://localhost:9870")
HDFS_URI = os.getenv("HDFS_URI", "hdfs://localhost:9000")
HDFS_USER = os.getenv("HADOOP_USER_NAME", "root")

DATALAKE_ROOT = os.getenv("DATALAKE_ROOT", "/datalake")
RAW_ROOT = f"{DATALAKE_ROOT}/raw"            # сжатые исходные файлы (csv.gz) как есть
CORE_ROOT = f"{DATALAKE_ROOT}/core"          # звезда: факты + измерения (Parquet/zstd)
MART_ROOT = f"{DATALAKE_ROOT}/marts"         # агрегированные витрины (Parquet/zstd)
QUARANTINE_ROOT = f"{DATALAKE_ROOT}/quarantine"
META_ROOT = f"{DATALAKE_ROOT}/_meta"         # манифесты загрузки, метрики качества, бенчмарки

TX_PER_MONTH = int(os.getenv("TX_PER_MONTH", "1000000"))
# Множитель объёма справочников (клиенты, счета, магазины, терминалы, мерчанты)
DATA_SCALE = float(os.getenv("DATA_SCALE", "3"))

# Описание источников: разделитель и состав файлов. Транзакции выгружаются помесячно,
# остальные таблицы — полный снимок (snapshot) на момент выгрузки.
SOURCES = {
    "bank1": {"sep": ",", "tables": ["clients", "accounts", "account_type", "account_status",
                                     "merchants", "terminals", "terminal_type", "terminal_status",
                                     "transaction_status", "currency"]},
    "bank2": {"sep": "|", "tables": ["clients", "accounts", "account_type", "account_status",
                                     "sellers", "terminals", "terminal_type",
                                     "transaction_status", "currency"]},
    "x5": {"sep": ",", "tables": ["stores", "store_types", "terminals", "terminal_types"]},
    "magnit": {"sep": ";", "tables": ["stores", "stores_type", "terminals"]},
}
BANKS = ["bank1", "bank2"]


def hdfs_url(path: str) -> str:
    return f"{HDFS_URI}{path}"
