# nf_project_spark — ELT-пайплайн пакетной аналитики (HDFS + Spark + Airflow)

Практическая работа № 2. Пайплайн забирает выгрузки двух банков и справочники торговых сетей
(источники из работы № 1), загружает их в HDFS в сжатом виде и преобразует Spark'ом
в оптимизированную для аналитики звёздную схему и витрины. Оркестрация — Apache Airflow,
аналитика — Jupyter + Spark SQL. Подробное обоснование и результаты — в [REPORT.md](REPORT.md).

```
 extract               load                      transform (Spark)                    analytics
┌──────────┐   ┌───────────────────┐   ┌──────────────────────────────┐   ┌──────────────────┐
│ landing  │   │ HDFS raw          │   │ core (Parquet+zstd)          │   │ marts (Parquet)  │
│ CSV на   │──▶│ csv.gz as-is      │──▶│ fact_transactions/txn_month= │──▶│ dm_daily_sales   │──▶ Jupyter
│ диске    │   │ batch=YYYY-MM     │   │ dim_terminal/client/account  │   │ dm_retailer_...  │    Spark SQL
└──────────┘   └───────────────────┘   │ quarantine (брак)            │   │ dm_client_...    │
                                       └──────────────────────────────┘   │ dm_hourly_load   │
                     Airflow DAG bank_elt (@monthly, catchup 2024-01…2024-12)  └──────────────────┘
   extract_to_landing ▶ load_raw_to_hdfs ▶ transform_raw_to_core ▶ dq_core ▶ build_marts ▶ dq_marts
```

## Стек

| Компонент | Версия | Роль |
|---|---|---|
| Hadoop HDFS (namenode + datanode) | 3.2.1 | хранилище data lake |
| Apache Spark standalone (master + worker) | 3.5.4 | трансформации и аналитика |
| Apache Airflow (LocalExecutor, Postgres) | 2.10.5 | оркестрация, расписание, ретраи, DQ-гейты |
| JupyterLab + PySpark | 4.2 / 3.5.4 | аналитика и отчёт |
| Python: pandas, numpy, hdfs (WebHDFS) | — | extract и load |

## Структура репозитория

```
docker-compose.yml        стенд: HDFS, Spark, Airflow, Jupyter
hadoop.env, airflow.env   конфигурация сервисов и пайплайна
docker/airflow/           образ Airflow + Java + pyspark (Spark-драйвер в client mode)
docker/jupyter/           образ Jupyter на базе apache/spark
dags/bank_elt.py          DAG bank_elt (месячные batch'и) и bank_elt_benchmark
pipeline/
  settings.py             пути слоёв, описание источников
  extract/generate.py     extract: выгрузки источников в landing (CSV)
  load/hdfs_loader.py     load: gzip-стриминг в HDFS raw + манифест
  spark_jobs/raw_to_core.py    transform 1: raw -> звезда (очистка, унификация, карантин)
  spark_jobs/core_to_marts.py  transform 2: core -> витрины
  spark_jobs/benchmark.py      замеры: размеры слоёв, кодеки, время запросов
  quality/checks.py       DQ-проверки между шагами
notebooks/                analytics.ipynb (собирается из build_notebook.py)
data_stores/              справочники X5/Магнит из работы №1 (seed для генератора)
migrations_pg, migrations_gp  схемы источников bank1 (PostgreSQL) и bank2 (Greenplum) из работы №1
```

## Запуск

Нужно: Docker + Compose, ~8 ГБ свободной RAM, ~8 ГБ диска.

```bash
make up          # сборка образов и запуск; Airflow поднимается ~1 мин
make run         # снять DAG bank_elt с паузы -> 12 месячных запусков (≈ 2 мин на месяц)
make benchmark   # после завершения: DAG bank_elt_benchmark
make notebook    # выполнить ноутбук с аналитикой (или открыть его в Jupyter)
make hdfs-ls     # размеры слоёв
```

| UI | адрес |
|---|---|
| Airflow | http://localhost:8080 (admin / admin) |
| HDFS NameNode | http://localhost:9870 (Utilities → Browse the file system) |
| Spark Master | http://localhost:8081 |
| Jupyter | http://localhost:8888 → `analytics.ipynb` |

Объём регулируется в `airflow.env`: `TX_PER_MONTH` (по умолчанию 1 000 000 транзакций bank1
в «средний» месяц, bank2 — 80% от этого) и `DATA_SCALE` (по умолчанию 3 — множитель
справочников: клиенты, счета, магазины, терминалы, мерчанты). С настройками по умолчанию за
12 месяцев получается 21.6 млн транзакций, 1.1 ГБ CSV только по транзакциям и 2.1 ГБ вместе
со снимками справочников (≈ 180 МБ на месяц).

Перезапуск месяца — Clear задачи/запуска в UI Airflow: все шаги идемпотентны (перезаписывают
только свою партицию batch/txn_month).

## Источники (extract)

`pipeline/extract/generate.py` эмулирует ежемесячные выгрузки систем из работы № 1 в
`data/landing/<source>/batch=YYYY-MM/`:

| источник | формат | особенности |
|---|---|---|
| bank1 (PostgreSQL) | CSV `,` | даты ISO, `merchants`, статусы `successful/pending/rejected` |
| bank2 (Greenplum) | CSV `\|` | даты `dd.mm.yyyy`, десятичная запятая, `sellers`, статусы `success/processing/failed` |
| x5 | CSV `,` | адрес разложен по колонкам |
| magnit | CSV `;` | адрес одной строкой `full_address`, «обл.», латиница в названиях регионов |

Справочники ритейлеров дополнены TID эквайера (`acquirer_bank`, `acquirer_terminal_id`) —
по нему терминал банка связывается с магазином. В транзакции подмешано ~0.05% брака
(дубли, пустые суммы, битые даты, несуществующие терминалы).
