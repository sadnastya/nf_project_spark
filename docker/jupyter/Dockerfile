FROM apache/spark:3.5.4-scala2.12-java17-python3-ubuntu

USER root
RUN pip3 install --no-cache-dir jupyterlab==4.2.5 pandas==2.1.4 numpy==1.26.4 matplotlib==3.8.4 pyarrow==16.1.0 \
    && mkdir -p /opt/notebooks /home/spark && chown -R spark:spark /opt/notebooks /home/spark \
    && chmod 777 /home/spark && chmod g+w /etc/passwd
COPY start-jupyter.sh /usr/local/bin/start-jupyter.sh

ENV PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip:/opt/src \
    PYSPARK_PYTHON=python3 \
    HOME=/home/spark

USER spark
WORKDIR /opt/notebooks
ENTRYPOINT ["/usr/local/bin/start-jupyter.sh"]
