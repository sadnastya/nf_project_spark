.PHONY: up down clean build extract-all run benchmark notebook hdfs-ls logs

up:            ## поднять стенд (HDFS, Spark, Airflow, Jupyter)
	@echo "AIRFLOW_UID=$$(id -u)" > .env
	mkdir -p data logs
	docker compose up -d --build

down:          ## остановить, данные HDFS сохраняются в volume
	docker compose down

clean:         ## остановить и удалить все данные (volumes, landing, логи)
	docker compose down -v
	rm -rf data logs

extract-all:   ## заранее выгрузить все 12 месяцев в landing (необязательно — DAG делает это сам)
	docker exec airflow-scheduler python -m pipeline.extract.generate --start 2024-01 --months 12

run:           ## снять DAG с паузы: Airflow прогонит 12 месячных batch'ей (catchup)
	docker exec airflow-scheduler airflow dags unpause bank_elt

benchmark:     ## бенчмарк форматов и запросов (после завершения bank_elt)
	docker exec airflow-scheduler airflow dags unpause bank_elt_benchmark
	docker exec airflow-scheduler airflow dags trigger bank_elt_benchmark

notebook:      ## пересобрать и выполнить ноутбук с аналитикой
	docker exec jupyter python3 /opt/notebooks/build_notebook.py
	docker exec jupyter jupyter nbconvert --to notebook --execute --inplace \
		--ExecutePreprocessor.timeout=1800 /opt/notebooks/analytics.ipynb

hdfs-ls:       ## структура хранилища
	docker exec namenode hdfs dfs -du -h /datalake /datalake/raw /datalake/core /datalake/marts

logs:
	docker compose logs -f airflow-scheduler
