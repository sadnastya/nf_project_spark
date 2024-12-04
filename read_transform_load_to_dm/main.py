from pyspark.sql import SparkSession
import SparkApp

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


files_csv=["x5_data/terminals.csv",
           "x5_data/terminal_types.csv",
           "x5_data/stores.csv",
           "x5_data/store_types.csv",
           
           "magnit_data/terminals.csv",
           "magnit_data/stores.csv",
           "magnit_data/stores_type.csv",
           ]
tables_stores=["x5_data/terminals.parquet",
           "x5_data/terminal_types.parquet",
           "x5_data/stores.parquet",
           "x5_data/store_types.parquet",
           "magnit_data/terminals.parquet",
           "magnit_data/stores.parquet",
           "magnit_data/stores_type.parquet"
           ]

if __name__ == "__main__":
    spark = (SparkSession.builder
                      .appName("My Spark App")
                      .master("local[2]")
                      .config("spark.driver.extraClassPath", "/home/asadovaia/drivers/postgresql-42.7.4.jar")\
                      .config("spark.sql", "true")\
                      .getOrCreate())

    app = SparkApp.SparkApp(spark)

    app.run(tables_pg,
            tables_gp,
            tables_stores,
            target_url="jdbc:postgresql://localhost:5432/postgres",
            usr="gpadmin",
            pwd="123456")