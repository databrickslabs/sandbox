# Databricks notebook source
# MAGIC %md
# MAGIC # Export to Databricks Notebooks
# MAGIC This notebook exports the converted code from the Delta table to Databricks notebooks. It iterates through the rows of the input table, retrieves the converted code, and then creates a corresponding Databricks notebook in the specified output directory.
# MAGIC
# MAGIC ## Task Overview
# MAGIC The following tasks are accomplished in this notebook:
# MAGIC
# MAGIC 1. **Load Data:** The data is loaded from the input table, which is the output of the previous conversion steps.
# MAGIC 2. **Prepare Notebook Content:** For each row in the table, the converted code is extracted and formatted into a Databricks notebook structure.
# MAGIC 3. **Export Notebooks:** The prepared notebooks are exported to the specified output directory using the `databricks-sdk` library.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC %pip install databricks-sdk --upgrade
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json
import os
from dataclasses import asdict

import pandas as pd
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

from scripts.notebook_export_helper import (ExportInput,
                                                      NotebookExportHelper)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
dbutils.widgets.text("result_table", "", "Conversion Result Table")
dbutils.widgets.text("output_dir", "", "Output Directory")

# COMMAND ----------

# DBTITLE 1,Load Configurations
result_table = dbutils.widgets.get("result_table")
output_dir = dbutils.widgets.get("output_dir")

result_table, output_dir

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC Parameter Name | Required | Description
# MAGIC --- | --- | ---
# MAGIC `result_table` | Yes | The name of the conversion result table created in the previous notebook.
# MAGIC `output_dir` | Yes | The directory where Databricks notebooks are saved. Supports the path in Workspace or Repos.

# COMMAND ----------

# DBTITLE 1,Enable Auto Reload Import Modules
# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

# DBTITLE 1,Prepare Export
helper = NotebookExportHelper()
df = spark.table(result_table)

exporter_inputs = [ExportInput(input_file_path=row['input_file_path'],
                               output_dir=output_dir,
                               code=row['result_content'],
                               python_parse_error=row['result_python_parse_error'],
                               sql_parse_error=row['result_sql_parse_errors'],
                               ) for row in df.collect()]
results = helper.process_notebooks(exporter_inputs)

# COMMAND ----------

# DBTITLE 1,Export Notebooks
ws_client = WorkspaceClient()

for output in results:
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(output.output_file_path), exist_ok=True)

    # Check the size of the encoded content
    if output.base64_encoded_content_size > 10 * 1024 * 1024:
        output.export_error = "Content size exceeds 10MB limit"
        continue

    try:
        # Export notebook
        ws_client.workspace.import_(
            content=output.base64_encoded_content,
            path=output.output_file_path,
            format=workspace.ImportFormat.SOURCE,
            language=workspace.Language.PYTHON,
            overwrite=True,
        )
        print(f"Exported notebook to {output.output_file_path}")
        output.export_succeeded = True
    except Exception as e:
        output.export_error = str(e)

# COMMAND ----------

# DBTITLE 1,Display Export Results
exclude_fields = {'base64_encoded_content'}
export_results_dict = [
    {k: v for k, v in output.__dict__.items() if k not in exclude_fields}
    for output in results
]
display(pd.DataFrame(export_results_dict))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Return the export results

# COMMAND ----------

# DBTITLE 1,Return Export Results
dbutils.notebook.exit(json.dumps(export_results_dict))
