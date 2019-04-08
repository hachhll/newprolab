from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark = SparkSession.builder.appName("SimpleStreamingApp").getOrCreate()

schema = StructType([
    StructField("timestamp", FloatType(), True),
    StructField("referer", StringType(), True),
    StructField("location", StringType(), True),
    StructField("remoteHost", StringType(), True),
    StructField("partyId", StringType(), True),
    StructField("sessionId", StringType(), True),
    StructField("pageViewId", StringType(), True),
    StructField("eventType", StringType(), True),
    StructField("item_id", StringType(), True),
    StructField("item_price", StringType(), True),
    StructField("item_url", StringType(), True),
    StructField("basket_price", StringType(), True),
    StructField("detectedDuplicate", StringType(), True),
    StructField("detectedCorruption", StringType(), True),
    StructField("firstInSession", StringType(), True),
    StructField("userAgentName", StringType(), True)
])


stream_from_kafka = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "35.197.203.81:6667") \
  .option("subscribe", "gevorg.hachaturyan") \
  .option("startingOffsets", "earliest") \
  .load()

tmp_df = stream_from_kafka \
    .select(stream_from_kafka['value'].cast("String")) \
    .select(F.from_json('value', schema).alias('value')) \
    .select('value.*')

query = tmp_df \
    .groupby('timestamp') \
    .count() \
    .writeStream \
    .trigger(processingTime="1 seconds") \
    .outputMode("complete") \
    .format("console") \
    .start()

query.awaitTermination()

