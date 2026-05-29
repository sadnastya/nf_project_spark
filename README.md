# nf_project_spark

## Общее описание

ETL-пайплайн для сбора, преобразования и загрузки банковских данных в витрины данных. Проект читает транзакционные данные из двух банковских систем (PostgreSQL и Greenplum), а также справочные данные о торговых точках двух ритейлеров (X5 и Магнит), выгружает всё в промежуточное хранилище HDFS в формате Parquet, затем джойнит и трансформирует данные через Spark и загружает итоговые витрины обратно в PostgreSQL.


## Стек технологий

| Категория | Технологии |
|---|---|
| Обработка данных | Apache Spark (PySpark), Pandas, PyArrow |
| Хранилище | Apache Hadoop (HDFS) |
| Базы данных | PostgreSQL, Greenplum |
| Форматы | Parquet, CSV |
| Миграции | Alembic |
| Язык | Python 3 |
| Драйверы | JDBC (postgresql-42.7.4.jar), PyWebHDFS, pyarrow.fs |

---

## Структура проекта

### `data_stores/`
Исходные CSV-файлы со справочными данными о торговых точках и терминалах двух ритейлеров.

- **`x5_data/`** — данные сети X5 Retail Group: магазины (`stores.csv`), типы магазинов (`store_types.csv`), терминалы (`terminals.csv`), типы терминалов (`terminal_types.csv`). Разделитель — запятая, адрес хранится в отдельных полях (регион, город, адрес).
- **`magnit_data/`** — данные сети Магнит: магазины (`stores.csv`), типы магазинов (`stores_type.csv`), терминалы (`terminals.csv`). Разделитель — точка с запятой, адрес хранится в одном поле `full_address` и требует парсинга при трансформации.


### `migrations_pg/`
Alembic-миграции и SQL-скрипты для инициализации схемы **bank1** в PostgreSQL.

- **`database_scripts/create_pg.sql`** — DDL-скрипт создания схемы `bank1`: таблицы клиентов, счетов, транзакций, мерчантов, терминалов и всех справочников (типы, статусы, валюты).
- **`database_scripts/test_data_pg.sql`** — вставка тестовых данных в схему bank1.
- **`versions/`** — ревизии Alembic: создание таблиц и наполнение тестовыми данными.
- **`alembic.ini`**, **`env.py`** — конфигурация подключения и среды для запуска миграций.


### `migrations_gp/`
Alembic-миграции и SQL-скрипты для инициализации схемы **bank2** в Greenplum.

Структура аналогична `migrations_pg/`, но адаптирована под Greenplum: все таблицы создаются с директивой `DISTRIBUTED BY(id)`. Схема называется `bank2`, а таблица продавцов называется `sellers` (вместо `merchants` в bank1).

- **`database_scripts/create_gplum.sql`** — DDL для Greenplum с распределением данных.
- **`database_scripts/test_data_gplum.sql`** — тестовые данные для bank2.
- **`versions/`** — ревизии Alembic для Greenplum.

### `upload_data_to_hdfs/`
Первый этап пайплайна: выгрузка данных из баз данных и CSV-файлов в HDFS.

- **`sparkApp.py`** — класс `SparkApp`, который читает таблицы из PostgreSQL (схема `bank1`) и Greenplum (схема `bank2`) через JDBC и сохраняет их в HDFS (`/data_bank/bank1/` и `/data_bank/bank2/`) в формате Parquet.
- **`pandasApp.py`** — класс `StoresData`, который читает CSV-файлы ритейлеров через Pandas, конвертирует в Parquet через PyArrow и записывает напрямую в HDFS (`/data_stores/`) через `pyarrow.fs.HadoopFileSystem`.
- **`main.py`** — точка входа: инициализирует SparkSession, запускает выгрузку банковских таблиц через `sparkApp`, затем итерируется по CSV-файлам ритейлеров и загружает их через `pandasApp`.


### `read_transform_load_to_dm/`
Второй этап пайплайна: чтение из HDFS, трансформация и загрузка в целевые витрины данных.

- **`SparkApp.py`** — основная логика трансформации:
  - Читает таблицы bank1 и bank2 из HDFS и загружает их напрямую в витрины `dm_bank1` и `dm_bank2` в PostgreSQL.
  - Для данных X5: джойнит терминалы, типы терминалов, магазины и типы магазинов в единую таблицу `terminals_info` с полями `terminal_id`, `terminal_type`, `store_region`, `store_address`, `store_type`.
  - Для данных Магнит: парсит поле `full_address` (разбивает на регион, город, улицу, номер дома), затем джойнит с терминалами и типами и формирует аналогичную таблицу `terminals_info`.
  - Все результаты пишутся в PostgreSQL через JDBC в режиме `overwrite`.
- **`main.py`** — точка входа: задаёт списки таблиц и путей, инициализирует SparkSession и вызывает `SparkApp.run()`.
- **`view_db.py`** — вспомогательный скрипт для проверки данных в целевой БД через Spark JDBC.
