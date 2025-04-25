# Databricks notebook source
# MAGIC %md
# MAGIC # Split Cells
# MAGIC This notebook is designed to split the converted Python code into multiple cells based on logical structure and control flow. The main objectives of this notebook are:
# MAGIC
# MAGIC 1. **Code Analysis**: Analyze the Python code to identify control structures and logical blocks.
# MAGIC 2. **Cell Splitting**: Use the CellSplitHelper to determine appropriate cell boundaries.
# MAGIC 3. **Cell Insertion**: Insert cell separators at the determined positions.
# MAGIC
# MAGIC ## Task Overview
# MAGIC The following tasks are accomplished in this notebook:
# MAGIC
# MAGIC 1. **Load Converted Code**: Extract the converted Python code from the result table.
# MAGIC 2. **Apply Cell Splitting**: Insert cell separators using the CellSplitHelper.
# MAGIC 3. **Save Results**: Store the updated code with cell separators back into the result table.
# MAGIC
# MAGIC This notebook plays a crucial role in improving the readability and executability of the converted code in the Databricks environment.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
from pyscripts.cell_split_helper import CellSplitHelper
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
# Required Parameters
dbutils.widgets.text("result_table", "", "Conversion Result Table (Required)")

# Required Parameters with Default Values
dbutils.widgets.dropdown("log_level", "INFO", ["DEBUG", "INFO"], "Logging Level")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC
# MAGIC Parameter Name | Required | Description | Default Value
# MAGIC --- | --- | --- | ---
# MAGIC `result_table` | Yes | The name of the conversion result table created in the previous notebook. |
# MAGIC `log_level` | Yes | The logging level to use for the cell splitting process. Options are `INFO` for standard logging or `DEBUG` for detailed debug information. | `INFO`

# COMMAND ----------

# DBTITLE 1,Load Configurations
# Load configurations from widgets
config_result_table = dbutils.widgets.get("result_table")
config_log_level = dbutils.widgets.get("log_level")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Extract Input Data

# COMMAND ----------

# DBTITLE 1,Extract Input Data
input_sdf = spark.sql(f"""
    SELECT
        input_file_number,
        result_content
    FROM {config_result_table}
    WHERE result_content IS NOT NULL
""")
display(input_sdf)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Apply Cell Splitting
# MAGIC The following applies cell splitting using the CellSplitHelper.

# COMMAND ----------

# DBTITLE 1,Apply Cell Splitting
cell_split_helper = CellSplitHelper(log_level=config_log_level)
split_cells_udf = udf(cell_split_helper.split_cells, StringType())
source_sdf = spark.table(config_result_table)

# Apply split_cells_udf to the dataframe
output_sdf = source_sdf.withColumn(
    "result_content",
    split_cells_udf(source_sdf.result_content)
)
display(output_sdf)

# COMMAND ----------

# DBTITLE 1,Save Result
output_sdf.write.mode("overwrite").saveAsTable(config_result_table)
print(f"Successfully saved result into the table: {config_result_table}")

# COMMAND ----------

# DBTITLE 1,Display Result Table
spark.table(config_result_table).display()
