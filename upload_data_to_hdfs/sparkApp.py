

class SparkApp:
    def __init__(self, spark):
        self.spark = spark


    def run(self, tables_pg, tables_gp, schema1, schema2, url1, usr1, pwd1, url2, usr2, pwd2):
        for table in tables_pg:
            self.read_save_table_from_db(url1,
                                 usr1,
                                 pwd1,
                                 schema1+table,
                                 "hdfs://localhost:9000/data_bank/bank1/"  + table)
        for table in tables_gp:
            self.read_save_table_from_db(url2,
                                 usr2,
                                 pwd2,
                                 schema2+table,
                                 "hdfs://localhost:9000/data_bank/bank2/"  + table)

    def read_save_table_from_db(self, url, user, password, dbtable, path_hdfs):

        df = self.spark.read.format("jdbc") \
            .option("url", url) \
            .option("user", user) \
            .option("password", password) \
            .option("dbtable", dbtable) \
            .load()

        df.write.mode("overwrite").parquet(path_hdfs)
