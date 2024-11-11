from pyspark.sql.functions import split

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
        
        for table in tables_stores:
            df = self.read_parquet("hdfs://localhost:9000/data_stores/"  + table)
            dir, table_name = table.split("/")
            if  dir == "x5_data":
                self.load_df_to_dm(df, target_url, target_schema1, usr, pwd, table_name.split(".")[0])
            
            if dir == "magnit_data":
                if table_name.split(".")[0] == "stores":
                    df =self.transform_address(df)
                self.load_df_to_dm(df, target_url, target_schema2, usr, pwd, table_name.split(".")[0])

    def read_parquet(self, path_hdfs):

        df = self.spark.read.format('parquet').options(header=True,inferSchema=True).load(path_hdfs)
        return df
    
    def load_df_to_dm(self, df,target_url, target_schema, usr, pwd, table):
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
        df.drop('full_address')
        return df

