# Databricks notebook source
import json

import pyspark.sql.functions as f
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import (
    StringType,
    MapType,
)

# COMMAND ----------


agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))
record_id = dbutils.widgets.get("record_id")
bronze_holding_table = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.bronze_holding_table'
)
silver_llm_responses = (
    f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.silver_llm_responses'
)
code_intent_table = f'{app_configs["CATALOG"]}.{app_configs["SCHEMA"]}.{app_configs["CODE_INTENT_TABLE_NAME"]}'

secret_scope = app_configs["DATABRICKS_TOKEN_SECRET_SCOPE"]
secret_key = app_configs["DATABRICKS_TOKEN_SECRET_KEY"]
host = app_configs["DATABRICKS_HOST"]

# COMMAND ----------

print(record_id)

# COMMAND ----------

# need this for when workspace client is created during a job
key = dbutils.secrets.get(scope=secret_scope, key=secret_key)


@pandas_udf(MapType(StringType(), StringType()))
def call_llm(input_code_series, agent_configs_series):
    def process_row(input_code, agent_configs):
        output = {}
        for agent in agent_configs.keys():
            agent_app_configs = agent_configs[agent]
            system_prompt = agent_app_configs["system_prompt"]
            endpoint = agent_app_configs["endpoint"]
            max_tokens = agent_app_configs["max_tokens"]
            temperature = agent_app_configs["temperature"]
            w = WorkspaceClient(host=host, token=key)
            messages = [
                ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=ChatMessageRole.USER, content=input_code),
            ]
            max_tokens = int(max_tokens)
            temperature = float(temperature)
            response = w.serving_endpoints.query(
                name=endpoint,
                max_tokens=max_tokens,
                messages=messages,
                temperature=temperature,
            )
            message = response.choices[0].message.content
            output[agent] = message
        return output

    return input_code_series.combine(agent_configs_series, process_row)


# COMMAND ----------

response = (
    spark.read.table(bronze_holding_table)
    .where(f.col("id") == f.lit(record_id))
    .withColumn("llm_responses", call_llm(f.col("content"), f.col("agentConfigs")))
    .withColumn("agentName", f.map_keys(f.col("agentConfigs")).getItem(0))
    .withColumn("agentResponse", f.map_values(f.col("llm_responses")).getItem(0))
    .select("path", "promptID", "loadDatetime", "content", "agentName", "agentResponse")
    .cache()
)

(response.write.mode("append").saveAsTable(silver_llm_responses))

# COMMAND ----------

temp_table_name = f"response{record_id}"
response.createOrReplaceTempView(temp_table_name)
spark.sql(
    f"""
MERGE INTO {code_intent_table} AS target
USING (
  SELECT hash(content) AS id, content AS code, agentResponse AS intent
  FROM {temp_table_name}
  WHERE agentName = "explanation_agent"
) AS source
ON target.id = source.id
WHEN MATCHED THEN
  UPDATE SET target.code = source.code, target.intent = source.intent
WHEN NOT MATCHED THEN
  INSERT (id, code, intent) VALUES (source.id, source.code, source.intent)
"""
)
