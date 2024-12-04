import sparkApp
from pyspark.sql import SparkSession
import pandasApp
import pyarrow.fs as fs
import os



schema1="bank1."

schema2="bank2."

tables_pg = ["accounts",
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

tables_gp = ["accounts",
          "transactions",
          "clients", 
          "account_type", 
          "account_status",  
          "transaction_type", 
          "transaction_status",
          "currency", 
          "sellers", 
          "terminal_type",
          "terminals"]

csv_load=pandasApp.StoresData()

path_csv_dir="data_stores/"
files_csv=["x5_data/terminals.csv",
           "x5_data/terminal_types.csv",
           "x5_data/stores.csv",
           "x5_data/store_types.csv",
           
           "magnit_data/terminals.csv",
           "magnit_data/stores.csv",
           "magnit_data/stores_type.csv",
           ]



HDFS_HOST = "localhost"  
HDFS_PORT = 9000    


connection = fs.HadoopFileSystem(host=HDFS_HOST, port=HDFS_PORT)




if __name__ == "__main__":
   spark = (SparkSession.builder
                      .appName("My Spark App")
                      .master("local[2]")
                      .config("spark.driver.extraClassPath", "/home/asadovaia/drivers/postgresql-42.7.4.jar")\
                      .getOrCreate())
   
   app = sparkApp.SparkApp(spark)

   app.run(tables_pg,
           tables_gp,
           schema1, 
           schema2, 
           "jdbc:postgresql://localhost:54320/postgres", 
           "postgres", 
           "password", 
           "jdbc:postgresql://localhost:5432/postgres", 
           "gpadmin", 
           "123456")
 

   for filepath in files_csv:
     if filepath.split("/")[0] == "x5_data":
        sep=','
     else:
        sep=';'
     csv_load.read_upload_data_from_csv(path_csv_dir + filepath, sep, connection, "/data_stores/"+filepath.split("/")[0]+"/"+os.path.splitext(os.path.basename(filepath))[0]+".parquet")
      
    
  