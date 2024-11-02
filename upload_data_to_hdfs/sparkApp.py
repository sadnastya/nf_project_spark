

class SparkApp:
    def __init__(self, spark):
        self.spark = spark

    def read_save_table_from_pg(self, url, user, password, dbtable, path_hdfs):

        df = self.spark.read.format("jdbc") \
            .option("url", url) \
            .option("user", user) \
            .option("password", password) \
            .option("dbtable", dbtable) \
            .load()

        df.write.mode("overwrite").parquet(path_hdfs)
