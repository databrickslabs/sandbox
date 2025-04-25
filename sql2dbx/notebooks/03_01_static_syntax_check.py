# Databricks notebook source
# MAGIC %md
# MAGIC # Static Syntax Check
# MAGIC This notebook performs a static syntax check on Python functions and the SQL statements extracted from these functions. The main goals of this notebook are:
# MAGIC
# MAGIC 1. **Python Function Syntax Check**: Using `ast.parse` to parse the input strings into an Abstract Syntax Tree (AST). Only correctly formatted Python functions can be parsed, thus ensuring static syntax correctness.
# MAGIC 2. **SQL Syntax Check**: Extracting SQL statements from the parsed Python functions and verifying their syntax using Spark's SQL parser.
# MAGIC
# MAGIC The extraction of SQL from Python functions is handled by the `spark_sql_extract_helper.py` script. The SQL syntax check is done using `EXPLAIN sql`.
# MAGIC
# MAGIC ## Task Overview
# MAGIC The following tasks are accomplished in this notebook:
# MAGIC
# MAGIC 1. **Load Data**: The data is loaded from the specified result table.
# MAGIC 2. **Parse Python Function and Extract SQL Statements**: Python functions are parsed using `ast.parse` to ensure they are valid, and SQL statements are extracted using the script.
# MAGIC 3. **Parse SQL Statements**: The extracted SQL statements are parsed to check for syntax errors using Spark's SQL parser.
# MAGIC 4. **Save Results**: The original data along with any syntax errors are saved back to the specified result table by adding new columns.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
from typing import List, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType, StructField, StructType
from pyscripts.spark_sql_extract_helper import SparkSQLExtractHelper

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
dbutils.widgets.text("result_table", "", "Conversion Result Table (Required)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC Parameter Name | Required | Description
# MAGIC --- | --- | ---
# MAGIC `result_table` | Yes | The name of the conversion result table created in the previous notebook.

# COMMAND ----------

# DBTITLE 1,Load Configurations
result_table = dbutils.widgets.get("result_table")
result_table

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display original table

# COMMAND ----------

# DBTITLE 1,Display Original
original_df = spark.table(result_table)
display(original_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parse Python function and extract SQL statements

# COMMAND ----------

# DBTITLE 1,Define UDF
def extract_sqls(func_string: str) -> Tuple[str, List[str]]:
    helper = SparkSQLExtractHelper()
    return helper.extract_sql_from_string(func_string)


extract_sqls_udf = udf(extract_sqls, StructType([
    StructField("result_python_parse_error", StringType(), True),
    StructField("result_extracted_sqls", ArrayType(StringType()), True)
]))

# COMMAND ----------

# DBTITLE 1,Parse Python and Extract SQLs
# Extract SQL from the result_content column, adding error messages and SQL list as new columns
new_df = original_df.withColumn("parsed_result", extract_sqls_udf("result_content"))

# Split parsed_result into two new columns: python_parse_error_str and extracted_sqls
new_df = (new_df
          .withColumn("result_python_parse_error", new_df["parsed_result"].getItem("result_python_parse_error"))
          .withColumn("result_extracted_sqls", new_df["parsed_result"].getItem("result_extracted_sqls"))
          .drop("parsed_result")
          )

# Display results
display(new_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parse SQL statements

# COMMAND ----------

# DBTITLE 1,Define SQL Parse Function
# Function to parse SQL statements on the driver
def parse_sql_statements(df: DataFrame) -> List[Tuple[str, List[str]]]:
    result = []
    rows = df.collect()
    for row in rows:
        errors_for_row = []
        for idx, sql in enumerate(row['result_extracted_sqls']):
            try:
                # Attempt to parse and plan the SQL without actually running it
                spark.sql(f"EXPLAIN {sql}")
            except Exception as e:
                error_message = str(e)
                # If the error message contains "JVM stacktrace", remove it
                jvm_index = error_message.find("JVM stacktrace:")
                if jvm_index != -1:
                    error_message = error_message[:jvm_index].strip()
                errors_for_row.append(f"Error in query {idx}: {error_message}")
        result.append((row["input_file_number"], errors_for_row))
    return result

# COMMAND ----------

# DBTITLE 1,Create DataFrame from Parsed Data
parsed_data = parse_sql_statements(new_df)
parsed_schema = StructType([
    StructField("input_file_number", StringType(), True),
    StructField("result_sql_parse_errors", ArrayType(StringType()), True)
])
parsed_errors_df = spark.createDataFrame(parsed_data, parsed_schema)
display(parsed_errors_df)

# COMMAND ----------

# DBTITLE 1,Add Parsed Errors to DataFrame
final_df = (new_df
            .drop("result_sql_parse_errors")
            .join(parsed_errors_df, on="input_file_number", how="left")
            )
display(final_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Update table

# COMMAND ----------

# DBTITLE 1,Update Table
final_df.write.mode("overwrite").saveAsTable(result_table)
print(f"Changes applied to the result table: {result_table}.")
