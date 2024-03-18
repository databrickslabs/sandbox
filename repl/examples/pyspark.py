from pyspark.sql.functions import sum, avg, count, window, col, to_date

df = spark.read.table("samples.nyctaxi.trips") \
    .filter(to_date(col("tpep_pickup_datetime")) == "2016-01-16") \
    .groupBy(window(col("tpep_pickup_datetime"), "1 hour").alias("pickup_hour")) \
    .agg(
        sum("fare_amount").alias("total_fares"),
        avg("fare_amount").alias("avg_fare"),
        count("*").alias("num_trips")
    ) \
    .orderBy(col("total_fares").desc()) \
    .limit(10)

display(df)
