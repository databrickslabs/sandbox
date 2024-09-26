# Databricks notebook source
import base64
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from pyspark.sql import functions as f
from pyspark.sql.types import *
import json

# COMMAND ----------

# DBTITLE 1,get params into notebook
agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))

secret_scope=app_configs["DATABRICKS_TOKEN_SECRET_SCOPE"]
secret_key=app_configs["DATABRICKS_TOKEN_SECRET_KEY"]
host=app_configs["DATABRICKS_HOST"]

workspace_location = app_configs["WORKSPACE_LOCATION"]
workspace_location = "/Workspace"+workspace_location

key = dbutils.secrets.get(scope=secret_scope, key=secret_key)

# COMMAND ----------

# DBTITLE 1,extract relevant variables from params

silver_llm_responses = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.silver_llm_responses'
)
gold_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.gold_transformed_notebooks'
)
prompt_id = dbutils.jobs.taskValues.get(taskKey="ingest_to_holding", key="promptID")
output_volume_path = app_configs["VOLUME_NAME_OUTPUT_PATH"]

# COMMAND ----------


# DBTITLE 1,function to write out a notebook as a string
@udf(StringType())
def write_notebook_code(llm_responses):
    for response in llm_responses:
        if "explanation_agent" == response[0]:
            explanation = response[1]
        elif "translation_agent" == response[0]:
            translated_code = response[1]

    template = """
-- Databricks notebook source
-- MAGIC %md
-- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
-- MAGIC
-- MAGIC ### AI Generated Intent
-- MAGIC
-- MAGIC INTENT_GOES_HERE

-- COMMAND ----------

TRANSLATED_CODE_GOES_HERE
  """

    output = template.replace("INTENT_GOES_HERE", explanation).replace(
        "TRANSLATED_CODE_GOES_HERE", translated_code
    )
    return output


# COMMAND ----------

# DBTITLE 1,write the notebooks into a new column
gold_df = (
  spark.read.table(silver_llm_responses)
  .filter(f.col("promptID") == f.lit(prompt_id))
  .withColumn("zipped", f.array(f.col("agentName"), f.col("agentResponse")) )
  .groupBy(
    f.col("content"),
    f.col("loadDatetime"),
    f.col("promptID"),
    f.col("path")
    )
  .agg(
    f.collect_list(f.col("zipped")).alias("zipped"),
    )
  .withColumn(
    "notebookAsString"
    ,write_notebook_code(f.col("zipped"))
    )
  .withColumn("path",f.split(f.col("path"),f.lit("\."))[0])
  .withColumn(
    "outputVolumePath"
    ,f.concat_ws("/", f.lit(output_volume_path), f.col("loadDatetime"), f.col("path"))
    )
  .withColumn(
    "outputNotebookPath"
    ,f.concat_ws("/", f.lit(workspace_location), f.lit("outputNotebooks"), f.col("loadDatetime"), f.col("path"))
    )
  .select(
    "promptID",
    "content",
    "loadDatetime",
    "notebookAsString",
    "outputVolumePath",
    "outputNotebookPath"
  )
)

gold_df.display()




# COMMAND ----------

temp_table_name = "gold_temp"
gold_df.createOrReplaceTempView(temp_table_name)
spark.sql(
    f"""
  INSERT INTO {gold_table} TABLE {temp_table_name}
  """
)
display(
    spark.sql(
        f"""
  select * from {gold_table}
  """
    )
)

# COMMAND ----------


pandas_gold = gold_df.toPandas()

temp_table_name = "gold_temp"
gold_df.createOrReplaceTempView(temp_table_name)
spark.sql(
    f"""
  INSERT INTO {gold_table} TABLE {temp_table_name}
  """
)
display(spark.sql(
    f"""
  select * from {gold_table}
  """
)
)
w = WorkspaceClient(
    host=host,
    token=key
)


def write_files(row):
    volume_path = row['outputVolumePath']
    content = row['notebookAsString']
    # write to a volume
    dbutils.fs.put(volume_path, content)

    # write to workspace

    notebook_path = row['outputNotebookPath']
    w.workspace.import_(
        content=base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        path=notebook_path,
        format=ImportFormat.SOURCE,
        language=Language.SQL,
        overwrite=True,
    )


pandas_gold = gold_df.toPandas()
pandas_gold.apply(write_files, axis=1)

# COMMAND ----------
