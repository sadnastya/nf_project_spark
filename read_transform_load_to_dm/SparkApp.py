from pyspark.sql.functions import split, lit, concat
class SparkApp:
    def __init__(self, spark):
        self.spark = spark
        
    
    def run(self, tables_pg, tables_gp, tables_stores, target_url, usr, pwd):
        
        for table in tables_pg:
            target_schema1 = "dm_bank1."
            df =self.read_parquet("hdfs://localhost:9000/data_bank/bank1/"  + table)
            self.load_df_to_dm(df, target_url, target_schema1, usr, pwd, table)

        for table in tables_gp:
            target_schema2 = "dm_bank2."
            df = self.read_parquet("hdfs://localhost:9000/data_bank/bank2/"  + table)
            self.load_df_to_dm(df, target_url, target_schema2, usr, pwd, table)
        dataframes1 = []
        dataframes2 = []
        for table in tables_stores:
            
            dir, table_name = table.split("/")
            if  dir == "x5_data":
                dataframes1.append(self.read_parquet("hdfs://localhost:9000/data_stores/"  + table))
                if len(dataframes1) == 4:
                    df = (dataframes1[0]
                          .join(dataframes1[1], dataframes1[0].terminal_type == dataframes1[1].id, "inner")
                          .join(dataframes1[2], dataframes1[0].store_id == dataframes1[2].id, "inner")
                          .join(dataframes1[3], dataframes1[2].store_type == dataframes1[3].id, "inner")
                          .select(
                            dataframes1[0].id.alias("terminal_id"),
                            dataframes1[1].type.alias("terminal_type"),
                            dataframes1[2].city.alias("store_region"),
                            dataframes1[2].address.alias("store_address"),
                            dataframes1[3].type.alias("store_type")
                            )
                        )
                    
                    self.load_df_to_dm(df, target_url, target_schema1, usr, pwd, "terminals_info")
            
            if dir == "magnit_data":
                df = self.read_parquet("hdfs://localhost:9000/data_stores/"  + table)
                if table_name.split(".")[0] == "stores":
                    df =self.transform_address(df)
                dataframes2.append(df)
                if len(dataframes2) == 3:
                    dataframes2[1].show()
                    df = (dataframes2[0]
                          .join(dataframes2[1], dataframes2[0].address == dataframes2[1].id, "inner")
                          .join(dataframes2[2], dataframes2[1].store_type == dataframes2[2].id, "inner")
                          .select(
                            dataframes2[0].id.alias("terminal_id"),
                            dataframes2[0].terminal_type.alias("terminal_type"),
                            dataframes2[1].city.alias("store_city"),
                            concat(dataframes2[1].street, lit(" "), dataframes2[1].house_number).alias("store_address"),
                            dataframes2[2].type.alias("store_type")
                            )
                        )
                    df.show()
                    self.load_df_to_dm(df, target_url, target_schema2, usr, pwd, "terminals_info")

    def read_parquet(self, path_hdfs):

        df = self.spark.read.format('parquet').options(header=True,inferSchema=True).load(path_hdfs)
        return df
    
    def load_df_to_dm(self, df, target_url, target_schema, usr, pwd, table):
        df.write.format('jdbc').options(
            url=target_url,
            dbtable=target_schema+table,
            user=usr,
            password=pwd).mode('overwrite').save()
    
    def transform_address(self, df):
        split_col = split(df['full_address'], ', ')
        df = df.withColumn('region', split_col.getItem(0)) \
            .withColumn('city', split_col.getItem(1)) \
            .withColumn('street', split_col.getItem(2)) \
            .withColumn('house_number', split_col.getItem(3))
        df =df.drop('full_address')
        return df

