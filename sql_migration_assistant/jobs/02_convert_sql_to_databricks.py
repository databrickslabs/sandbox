# Databricks notebook source
# MAGIC %md
# MAGIC # Convert SQL to Databricks
# MAGIC This notebook facilitates the conversion of SQL-based workflows such as T-SQL Stored Procedures into Databricks-compatible code, allowing for the seamless migration to the Databricks environment.
# MAGIC
# MAGIC This notebook is inspired by the following reference: [chat-batch-inference-api - Databricks](https://learn.microsoft.com/en-us/azure/databricks/_extras/notebooks/source/machine-learning/large-language-models/chat-batch-inference-api.html).
# MAGIC
# MAGIC ## Task Overview
# MAGIC The following tasks are accomplished in this notebook:
# MAGIC
# MAGIC 1. **Read Data**: Data is read from the input table and specified columns. The input table is assumed to have been created in the preceding notebook (<a href="$./01_analyze_input_files" target="_blank">01_analyze_input_files</a>), and the `input_file_content_without_sql_comments` column is utilized for processing.
# MAGIC 2. **Request Construction and Submission**: Requests are constructed and sent to the specified Databricks model serving endpoint with concurrent processing.
# MAGIC 3. **Persist Results**: The results of the conversion process are added to the input table.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json
import logging

from scripts.batch_inference_helper import (AsyncChatClient,
                                            BatchInferenceManager,
                                            BatchInferenceRequest)
from scripts.system_prompts.tsql_conversion_prompt import \
    TsqlConversionPromptManager

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters
# MAGIC

# COMMAND ----------

# DBTITLE 1,Configurations
# Required Parameters
dbutils.widgets.text("endpoint_name", "", "Serving Endpoint Name (Required)")
dbutils.widgets.text("result_table", "", "Conversion Result Table (Required)")

# Optional Parameters
dbutils.widgets.dropdown("sql_dialect", "tsql", ["tsql"], "SQL Dialect")
dbutils.widgets.dropdown("comment_lang", "English", ["English", "Japanese"], "Comment Language")
dbutils.widgets.text("request_params", '{"max_tokens": 4000, "temperature": 0}', "Chat Request Params")
dbutils.widgets.text("concurrency", "10", "Concurrency Requests")

dbutils.widgets.text("logging_interval", "1", "Logging Interval")
dbutils.widgets.text("timeout", "300", "Timeout Seconds")
dbutils.widgets.text("max_retries_backpressure", "20", "Max Retries on Backpressure")
dbutils.widgets.text("max_retries_other", "5", "Max Retries on Other Errors")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC
# MAGIC Parameter Name | Required | Default Value | Description
# MAGIC --- | --- | --- | ---
# MAGIC `endpoint_name` | Yes |  | The name of the Databricks Model Serving endpoint. You can find the endpoint name under the `Serving` tab. Example: If the endpoint URL is `https://<workspace_url>/serving-endpoints/hinak-oneenvgpt4o/invocations`, specify `hinak-oneenvgpt4o`.
# MAGIC `result_table` | Yes |  | The name of the conversion result table created in the previous notebook.
# MAGIC `sql_dialect` | Yes | `tsql` | The SQL dialect to be converted. Currently, only tsql is supported.
# MAGIC `comment_lang` | Yes | `English` | The language for comments to be added to the converted Databricks notebooks. Options are English or Japanese.
# MAGIC `concurrency` | Yes | `10` | The number of concurrent requests sent to the model serving endpoint.
# MAGIC `logging_interval` | Yes | `1` | The number of requests processed before logging a progress update. Controls the frequency of progress reports during batch processing, showing the total requests processed and elapsed time.
# MAGIC `timeout` | Yes | `300` | The timeout for an HTTP request on the client side, in seconds.
# MAGIC `max_retries_backpressure` | Yes | `20` | The maximum number of retries on backpressure status code (such as `429` or `503`).
# MAGIC `max_retries_other` | Yes | `5` | The maximum number of retries on other errors (such as `5xx`, `408`, or `409`).
# MAGIC `request_params` | Yes | `{"max_tokens": 4000, "temperature": 0}` | The extra chat HTTP request parameters in JSON format (reference: [Databricks Foundation Model APIs](https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request)).

# COMMAND ----------

# DBTITLE 1,Load Configurations
# Load configurations from widgets
config_endpoint_name = dbutils.widgets.get("endpoint_name")
config_timeout = int(dbutils.widgets.get("timeout"))
config_max_retries_backpressure = int(dbutils.widgets.get("max_retries_backpressure"))
config_max_retries_other = int(dbutils.widgets.get("max_retries_other"))

config_request_params = json.loads(
    dbutils.widgets.get("request_params")
)  # Reference: https://docs.databricks.com/en/machine-learning/foundation-models/api-reference.html#chat-request

config_concurrecy = int(dbutils.widgets.get("concurrency"))
config_logging_interval = int(dbutils.widgets.get("logging_interval"))

config_result_table = dbutils.widgets.get("result_table")
config_sql_dialect = dbutils.widgets.get("sql_dialect")
config_comment_lang = dbutils.widgets.get("comment_lang")

# COMMAND ----------

# MAGIC %md
# MAGIC ## System message & few-shots by SQL dialect
# MAGIC **Note**: Currently, the notebook supports only the `tsql` dialect. Support for additional dialects may be added in the future. You can specify your custom prompts (`system_message` and `few_shots`) by modifying the code below.

# COMMAND ----------

# DBTITLE 1,Enable Auto Reload Import Modules
# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

# DBTITLE 1,System Message and Few-Shots
if config_sql_dialect == "tsql":
    manager = TsqlConversionPromptManager(config_comment_lang)
    system_message = manager.get_system_message()
    few_shots = manager.get_few_shots()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run batch inference
# MAGIC The following code loads a Spark dataframe of the input data table and then converts that dataframe into a list of text that the model can process.

# COMMAND ----------

# DBTITLE 1,Create Batch Inference Requests
source_sdf = spark.table(config_result_table)
input_sdf = (source_sdf
    .filter("is_conversion_target == true")
    .select(
        "input_file_number",
        "input_file_content_without_sql_comments")
)
input_df = input_sdf.toPandas()

batch_inference_requests = [
    BatchInferenceRequest(
        index=int(row[0]),
        text=row[1],
        system_message=system_message,
        few_shots=few_shots)
    for row in input_df.itertuples(index=False, name=None)
]

# COMMAND ----------

# DBTITLE 1,Display Batch Inference Requests
display_df = spark.createDataFrame([
    (req.index, req.text, req.system_message, str(req.few_shots))
    for req in batch_inference_requests
], ["index", "text", "system_message", "few_shots"])

display(display_df)

# COMMAND ----------

# MAGIC %md
# MAGIC The following records and stores the batch inference responses.

# COMMAND ----------

# DBTITLE 1,Create Batch Inference Manager
batch_manager = BatchInferenceManager(
    client=AsyncChatClient(
        endpoint_name=config_endpoint_name,
        request_params=config_request_params,
        timeout=config_timeout,
        max_retries_backpressure=config_max_retries_backpressure,
        max_retries_other=config_max_retries_other,
        log_level=logging.INFO,
    ),
    concurrency=config_concurrecy,
    logging_interval=config_logging_interval,
    log_level=logging.INFO,
)

# COMMAND ----------

# DBTITLE 1,Batch Inference
batch_inference_responses = await batch_manager.batch_inference(batch_inference_requests)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save results
# MAGIC The following stores the output to the result table and displays the results

# COMMAND ----------

# DBTITLE 1,Load Notebook Utils
# MAGIC %run ./notebook_utils

# COMMAND ----------

# DBTITLE 1,Organize Output
batch_inference_result_processor = BatchInferenceResultProcessor(model_serving_endpoint_for_conversion=config_endpoint_name)
output_sdf = batch_inference_result_processor.process_results(source_sdf, batch_inference_responses)
display(output_sdf)

# COMMAND ----------

# DBTITLE 1,Save Result
output_sdf.write.mode("overwrite").saveAsTable(config_result_table)
print(f"Successfully saved result into the table: {config_result_table}")

# COMMAND ----------

# DBTITLE 1,Display Result Table
spark.table(config_result_table).display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Cleaning results
# MAGIC The following performs cleaning on `result_content`. The reason for saving the data first and then performing cleaning is to enable time travel in case there are any issues with the cleaning process.

# COMMAND ----------

# DBTITLE 1,Clean Result
cleand_df = clean_conversion_results(config_result_table)
display(cleand_df)

# COMMAND ----------

# DBTITLE 1,Save Cleaned Result
cleand_df.write.mode("overwrite").saveAsTable(config_result_table)
print(f"Successfully saved cleaned result into the table: {config_result_table}")

# COMMAND ----------

# DBTITLE 1,Display Cleaned Result Table
spark.table(config_result_table).display()
