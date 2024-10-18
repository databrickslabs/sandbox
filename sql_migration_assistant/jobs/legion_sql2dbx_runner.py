# Databricks notebook source
# MAGIC %md
# MAGIC # Legion to sql2dbx Runner Notebook
# MAGIC
# MAGIC This notebook serves as a bridge between Project Legion and the main notebook of sql2dbx. It maps configuration parameters from Legion's `agent_configs` and `app_configs` to those required by sql2dbx, and then runs its main notebook.
# MAGIC
# MAGIC ## Overview
# MAGIC - **Purpose**: Integrate Legion's configuration with sql2dbx.
# MAGIC - **Functionality**:
# MAGIC   - Extract necessary parameters from `agent_configs` and `app_configs`.
# MAGIC   - Map these parameters to match sql2dbx's requirements.
# MAGIC   - Run sql2dbx's main notebook with the mapped parameters.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Import Libraries
# MAGIC
# MAGIC Import necessary Python libraries for JSON handling.

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Retrieve Configuration Parameters
# MAGIC
# MAGIC Fetch `app_configs` and `agent_configs`, which are provided as inputs from Legion.

# COMMAND ----------

# DBTITLE 1,Retrieve Configuration Parameters
agent_configs = json.loads(dbutils.widgets.get("agent_configs"))
app_configs = json.loads(dbutils.widgets.get("app_configs"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Extract Translation Agent Parameters
# MAGIC
# MAGIC Extract parameters from the `translation_agent` configuration to be used in sql2dbx's main notebook.

# COMMAND ----------

# DBTITLE 1,Extract Translation Agent Parameters
translation_agent = agent_configs[0][0]["translation_agent"]

# Build the request_params dictionary for sql2dbx
request_params = {
    "max_tokens": translation_agent["max_tokens"],
    "temperature": translation_agent["temperature"],
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Map Parameters for sql2dbx's Main Notebook
# MAGIC
# MAGIC Map the extracted parameters to those required by sql2dbx's main notebook.

# COMMAND ----------

# DBTITLE 1,Map Parameters
notebook_params = {
    "input_dir": app_configs.get("VOLUME_NAME_INPUT_PATH", ""),
    "result_catalog": app_configs.get("CATALOG", ""),
    "result_schema": app_configs.get("SCHEMA", ""),
    "endpoint_name": translation_agent.get("endpoint", ""),
    "sql_dialect": "tsql",  # Currently only 'tsql' is supported
    "request_params": json.dumps(request_params),
    "output_dir": app_configs.get("VOLUME_NAME_OUTPUT_PATH", ""),

    # TODO: Currently using default values for the following params; consider making them configurable.
    # "token_count_threshold": app_configs.get("MAX_TOKENS", "20000"),
    # "comment_lang": app_configs.get("COMMENT_LANGUAGE", "English"),
    # "max_fix_attempts": app_configs.get("MAX_FIX_ATTEMPTS", "1"),
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Execute sql2dbx's Main Notebook
# MAGIC
# MAGIC Run sql2dbx's main notebook with the mapped parameters.

# COMMAND ----------

# DBTITLE 1,Execute sql2dbx's Main Notebook
dbutils.notebook.run("sql2dbx/00_main", timeout_seconds=0, arguments=notebook_params)
