# Databricks notebook source
# MAGIC %md
# MAGIC # Assign the table config JSON you would like to debug to variable `table_config`
# MAGIC For example,
# MAGIC ```
# MAGIC table_config = r'''
# MAGIC {
# MAGIC   "name": "all_employees",
# MAGIC   "format": "csv",
# MAGIC   "format_options": {
# MAGIC     "header": "true",
# MAGIC     "escape": "\""
# MAGIC   }
# MAGIC   "schema_hints": "id int, name string"
# MAGIC }
# MAGIC '''
# MAGIC ```

# COMMAND ----------

table_config = r'''
{
  "name": "all_employees",
  "format": "csv",
  "format_options": {
    "header": "true",
    "escape": "\""
  },
  "schema_hints": "id int, name string"
}
'''

# COMMAND ----------

import json
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import NotFound

# Initialize workspace client
ws = WorkspaceClient()

# Load configs from environment json
environment_path = "./configs/environment.json"
assert os.path.exists(environment_path), f"Missing environment file: {environment_path}. Have you run `databricks bundle run configuration_job`?"
with open(environment_path, "r") as f:
  configs = json.load(f)

catalog_name = configs["catalog_name"]
schema_name = configs["schema_name"]
table_config_json = json.loads(table_config)
table_name = table_config_json["name"]
assert table_name, "Please provide a table name in the table_config"

# Load table configs
table_configs_path = "./configs/tables.json"
assert os.path.exists(table_configs_path), f"Missing table configs file: {table_configs_path}. Please following README.md to create one, deploy and run configuration_job."
with open(table_configs_path, "r") as f:
  table_configs = json.load(f)
matches = [table_config for table_config in table_configs if table_config.get("name") == table_name]
assert len(matches) == 1, f"Expect exactly 1 config for table `{table_name}`. Found {len(matches)}. Please fix the config file and run configuration_job"

table_volume_path_data = configs["volume_path_data"] + f"/{table_name}"
try:
  ws.files.get_directory_metadata(table_volume_path_data)
  iter = ws.files.list_directory_contents(table_volume_path_data)
  next(iter)
except NotFound:
  assert False, f"Table data path not found for table `{table_name}`. Have you run `databricks bundle run configuration_job`?"
except StopIteration:
  assert False, f"No data file found in {table_volume_path_data}. Please upload at least 1 file."

print(f"Table Volume Path: {table_volume_path_data}")
print(f"Table Config:\n{table_config}")

# COMMAND ----------

import tempfile
from utils import configmanager

with tempfile.TemporaryDirectory() as tmpdir:
  reader = spark.readStream.format("cloudFiles")
  reader = configmanager.apply_table_config(reader, table_config_json)
  reader.option("cloudFiles.schemaLocation", tmpdir)
  display(reader.load(table_volume_path_data))
