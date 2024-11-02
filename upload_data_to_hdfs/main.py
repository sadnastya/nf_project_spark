import sparkApp
from pyspark.sql import SparkSession
import pandasApp
from hdfs import InsecureClient
import os


spark = (SparkSession.builder
                      .appName("My Spark App")
                      .master("local[2]")
                      .config("spark.driver.extraClassPath", "/home/asadovaia/drivers/postgresql-42.7.4.jar")\
                      .getOrCreate())
schema="bank1."

app = sparkApp.SparkApp(spark)
tables = ["accounts",
          "transactions",
          "clients", 
          "account_type", 
          "account_status",  
          "transaction_type", 
          "transaction_status",
          "currency", 
          "merchants", 
          "terminal_status", 
          "terminal_type",
          "terminals"]

csv_load=pandasApp.StoresData()

path_csv_dir="data_stores/"
files_csv=["x5_data/stores.csv",
           "x5_data/store_types.csv",
           "x5_data/terminals.csv",
           "x5_data/terminal_types.csv",
           "magnit_data/stores.csv",
           "magnit_data/store_type.csv",
           "magnit_data/terminals.csv"]

client = InsecureClient("http://localhost:9000")
client.makedirs("/data_stores")


if __name__ == "__main__":
  #  for table in tables:
  #    app.read_save_table_from_pg("jdbc:postgresql://localhost:54320/postgres",
  #                                "postgres",
  #                                "password",
  #                                schema+table,
  #                                "hdfs://localhost:9000/data_bank/bank1/"  + table)

   for filepath in files_csv:
     csv_load.read_upload_data_from_csv(path_csv_dir + filepath, client, "hdfs://localhost:9000/data_stores/"+os.path.splitext(os.path.basename(filepath))[0]+".parquet")
      
    
  