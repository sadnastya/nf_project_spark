"""ELT-пайплайн пакетной аналитики: landing (CSV) -> HDFS raw (csv.gz) -> core (Parquet) -> marts.

Один запуск DAG = один месячный batch (data_interval_start). Все шаги идемпотентны:
повторный запуск перезаписывает только свою партицию, поэтому безопасны retries и
перезапуск любого месяца через Clear в UI.
"""
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

from pipeline.extract.generate import extract_batch
from pipeline.load.hdfs_loader import load_batch
from pipeline.quality import checks

BATCH = "{{ data_interval_start.strftime('%Y-%m') }}"
JOBS_DIR = "/opt/airflow/pipeline/spark_jobs"
SPARK_CONF = {
    "spark.executor.memory": "1536m",
    "spark.executor.cores": "2",
    "spark.cores.max": "4",
    "spark.sql.shuffle.partitions": "16",
}


def spark_task(task_id: str, script: str, args=None) -> SparkSubmitOperator:
    return SparkSubmitOperator(
        task_id=task_id,
        conn_id="spark_default",
        application=f"{JOBS_DIR}/{script}",
        application_args=args if args is not None else ["--batch", BATCH],
        name=f"{task_id}_{{{{ ds_nodash }}}}",
        conf=SPARK_CONF,
        driver_memory="1g",
        env_vars={"PYTHONPATH": "/opt/airflow"},
    )


def dq(check):
    def _run(batch):
        try:
            return check(batch)
        except checks.DataQualityError as e:  # брак данных не лечится ретраем
            raise AirflowFailException(str(e)) from e
    return _run


default_args = {"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=1),
                "execution_timeout": timedelta(minutes=30)}

with DAG(
    dag_id="bank_elt",
    description="Транзакции банков + справочники X5/Магнит: HDFS + Spark, помесячные батчи",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    end_date=pendulum.datetime(2024, 12, 31, tz="UTC"),
    schedule="@monthly",
    catchup=True,
    max_active_runs=1,
    default_args=default_args,
    doc_md=__doc__,
    tags=["elt", "spark", "hdfs"],
) as dag:
    extract = PythonOperator(
        task_id="extract_to_landing", python_callable=extract_batch, op_kwargs={"batch": BATCH},
        doc_md="Выгрузка источников за месяц в landing-зону на диске (CSV).")
    load = PythonOperator(
        task_id="load_raw_to_hdfs", python_callable=load_batch, op_kwargs={"batch": BATCH},
        doc_md="Потоковое gzip-сжатие файлов и загрузка в /datalake/raw через WebHDFS.")
    core = spark_task("transform_raw_to_core", "raw_to_core.py")
    dq_core = PythonOperator(task_id="dq_core", python_callable=dq(checks.check_core),
                             op_kwargs={"batch": BATCH})
    marts = spark_task("build_marts", "core_to_marts.py")
    dq_marts = PythonOperator(task_id="dq_marts", python_callable=dq(checks.check_marts),
                              op_kwargs={"batch": BATCH})

    extract >> load >> core >> dq_core >> marts >> dq_marts


with DAG(
    dag_id="bank_elt_benchmark",
    description="Сравнение форматов хранения и времени аналитических запросов (raw vs core vs marts)",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["elt", "spark", "report"],
) as bench_dag:
    spark_task("benchmark_storage_and_queries", "benchmark.py", args=[])
