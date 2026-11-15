from pyspark.sql import SparkSession

print("Starting Spark...")

spark = (
    SparkSession.builder
    .appName("MovieTest")
    .master("local[*]")
    .getOrCreate()
)

print("Spark started successfully!")

spark.stop()
