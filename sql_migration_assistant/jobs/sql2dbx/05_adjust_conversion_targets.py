# Databricks notebook source
# MAGIC %md
# MAGIC # Adjust Conversion Targets
# MAGIC This notebook allows you to refine the selection of files for conversion from SQL to Databricks notebooks. By adjusting the `is_conversion_target` field in the target table, you can control which files are included or excluded in the conversion process. This is particularly useful after an initial conversion attempt, allowing you to focus on specific files that failed to convert or require adjustments before re-conversion.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
from pyspark.sql.functions import col, when
from scripts import utils

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
dbutils.widgets.text("result_table", "", "Conversion Result Table")
dbutils.widgets.text("set_true_numbers", "", "Set True Numbers")
dbutils.widgets.text("set_false_numbers", "", "Set False Numbers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC Parameter Name | Required | Description
# MAGIC --- | --- | ---
# MAGIC `result_table` | Yes | The name of the conversion result table created in the previous notebook.
# MAGIC `set_true_numbers` | No | A comma-separated list or range of `input_file_number` values to set `is_conversion_target` to True (e.g., `1, 2-4, 5-6, 7` which sets 1 through 7 as targets).
# MAGIC `set_false_numbers` | No | A comma-separated list or range of `input_file_number` values to set `is_conversion_target` to False (e.g., `1, 2-4, 5-6, 7` which sets 1 through 7 as non-targets).

# COMMAND ----------

# DBTITLE 1,Load Configurations
result_table = dbutils.widgets.get("result_table")
set_true_numbers = utils.parse_number_ranges(dbutils.widgets.get("set_true_numbers"))
set_false_numbers = utils.parse_number_ranges(dbutils.widgets.get("set_false_numbers"))

result_table, set_true_numbers, set_false_numbers

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display table before update

# COMMAND ----------

# DBTITLE 1,Display Original
original_df = spark.table(result_table)
display(original_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Update table

# COMMAND ----------

# DBTITLE 1,Update Table
update_df = original_df.withColumn(
    "is_conversion_target",
    when(col("input_file_number").isin(set_true_numbers), True)
    .when(col("input_file_number").isin(set_false_numbers), False)
    .otherwise(col("is_conversion_target")),
)

display(update_df)

# COMMAND ----------

# DBTITLE 1,Writing Output to a Table
if set_true_numbers or set_false_numbers:
    update_df.write.mode("overwrite").saveAsTable(result_table)
    print(f"Changes applied to the result table: {result_table}.")
else:
    print("No changes applied to the result table: {result_table} because the parameters are empty.")
