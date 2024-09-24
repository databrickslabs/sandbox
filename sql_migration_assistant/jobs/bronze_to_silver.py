# Databricks notebook source
# DBTITLE 1,get params
import json
from pyspark.sql.types import (
    ArrayType,
    StructType,
    StructField,
    StringType,
    MapType,
    IntegerType,
    TimestampType,
)
import pyspark.sql.functions as f
from pyspark.sql.functions import udf, pandas_udf

agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))

# COMMAND ----------

print(agent_configs)

# COMMAND ----------

print(app_configs)

# COMMAND ----------

checkpoint_dir = app_configs["VOLUME_NAME_CHECKPOINT_PATH"]
volume_path = app_configs["VOLUME_NAME_INPUT_PATH"]

# COMMAND ----------

dbutils.fs.rm(checkpoint_dir, True)

# COMMAND ----------

bronze_raw_code = f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.bronze_raw_code'
spark.sql(f"""drop table if exists {bronze_raw_code}""")
spark.sql(
    f"""
  CREATE TABLE IF NOT EXISTS {bronze_raw_code} (
    path STRING,
    modificationTime TIMESTAMP, 
    length INT,
    content STRING,
    --content BINARY,
    loadDatetime TIMESTAMP
    )
  """
)

bronze_prompt_config = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.bronze_prompt_config'
)
spark.sql(f"""drop table if exists {bronze_prompt_config}""")
spark.sql(
    f"""
  CREATE TABLE IF NOT EXISTS {bronze_prompt_config} (
    promptID INT,
    agentConfigs MAP <STRING, MAP <STRING, STRING>>,
    loadDatetime TIMESTAMP
    )
  """
)

bronze_holding_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.bronze_holding_table'
)
spark.sql(f"""drop table if exists {bronze_holding_table}""")
spark.sql(
    f"""
  CREATE TABLE IF NOT EXISTS {bronze_prompt_config} (
    id INT,
    path STRING,
    modificationTime TIMESTAMP,
    length INT,
    content STRING,
    loadDatetime TIMESTAMP,
    promptID INT,
    agentConfigs MAP <STRING, MAP <STRING, STRING>>
    )
  """
)


silver_llm_responses = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.silver_llm_responses'
)
spark.sql(f"""drop table if exists {silver_llm_responses}""")
spark.sql(
    f"""
  CREATE TABLE IF NOT EXISTS {silver_llm_responses} (
    path STRING,
    promptID INT,
    loadDatetime TIMESTAMP,
    content STRING, 
    agentName STRING,
    agentResponse STRING
    )
  """
)


gold_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.gold_transformed_notebooks'
)
spark.sql(f"""drop table if exists {gold_table}""")
spark.sql(
    f"""
  CREATE TABLE IF NOT EXISTS {gold_table} (
    promptID INT,  
    content STRING,
    loadDatetime TIMESTAMP,
    path STRING, 
    notebookAsString STRING,
    outputPath STRING
    )
  """
)


# COMMAND ----------

# DBTITLE 1,convert agent_configs input string to a dataframe
import pyspark.sql.functions as f

schema = StructType(
    [
        StructField(
            "agentConfigs",
            MapType(StringType(), MapType(StringType(), StringType())),
            True,
        )
    ]
)
agent_configs_df = (
    spark.createDataFrame(agent_configs, schema)
    .withColumn("loadDatetime", f.current_timestamp())
    .withColumn("promptID", f.hash(f.col("loadDatetime").cast("STRING")))
    .select(f.col("promptID"), f.col("agentConfigs"), f.col("loadDatetime"))
)
# display(agent_configs_df)

agent_configs_df.createOrReplaceTempView("temp_configs")
spark.sql(f"INSERT INTO {bronze_prompt_config} TABLE temp_configs")
spark.sql(f"select * from {bronze_prompt_config}").display()

# COMMAND ----------

# DBTITLE 1,load code files

raw_stream = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("wholetext", True)
    .load(volume_path)
    .withColumn("loadDatetime", f.current_timestamp())
    .withColumn(
        "modificationTime", f.current_timestamp()
    )  # I'm not sure how to populate this
    .withColumn("path", f.col("_metadata.file_name"))
    .withColumnRenamed("value", "content")
    .withColumn("length", f.length(f.col("content")))
    # .withColumn("content", f.to_binary(f.col("content")))
    .select(
        f.col("path"),
        f.col("modificationTime"),
        f.col("length"),
        f.col("content"),
        f.col("loadDatetime"),
    )
)

(
    raw_stream.writeStream.format("delta")
    .outputMode("append")
    .option("checkpointLocation", checkpoint_dir)
    .trigger(availableNow=True)
    .table(bronze_raw_code)
    .processAllAvailable()
)

display(spark.sql(f"select * from {bronze_raw_code}"))

# COMMAND ----------

# DBTITLE 1,get the prompts which are greater than the loaddate in the silver table

llm_inputs = spark.sql(
    f"""
  select monotonically_increasing_id() as id, * from {bronze_raw_code}
  cross join (
    select bpc.promptID, agentConfigs
    from {bronze_prompt_config} bpc
    left join {silver_llm_responses} st on bpc.loadDatetime > st.loadDatetime  
  )
  """
)
llm_inputs.write.saveAsTable(bronze_holding_table)
display(spark.read.table(bronze_holding_table))

# COMMAND ----------

# get the id's that will be passed to the for each loop for llm'ing
ids = llm_inputs.select("id").collect()
ids = [x.id for x in ids]
dbutils.jobs.taskValues.set(key="new_record_ids", value=ids)

# set the promptID as a value. This will be used fo the gold table to pull in
# the latest results from the silver table
promptID = llm_inputs.select("promptID").distinct().collect()
promptID = [x.promptID for x in promptID][0]
dbutils.jobs.taskValues.set(key="promptID", value=promptID)
