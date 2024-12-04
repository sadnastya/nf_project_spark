from pyspark.sql import SparkSession
import SparkApp

spark = (SparkSession.builder
                      .appName("My Spark App")
                      .master("local[2]")
                      .config("spark.driver.extraClassPath", "/home/asadovaia/drivers/postgresql-42.7.4.jar")\
                      .config("spark.sql", "true")\
                      .getOrCreate())

def bank1(spark):
    df = spark.read.format("jdbc") \
            .option("url", "jdbc:postgresql://localhost:5432/postgres") \
            .option("user", "gpadmin") \
            .option("password", "123456") \
            .option("dbtable", "") \
            .load()