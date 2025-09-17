# Databricks notebook source
# MAGIC %md
# MAGIC # Paste the table config JSON you would like to debug and assign to variable `table_config`
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
from utils import envmanager
from utils import tablemanager

# Load configs from environment json
config = envmanager.get_config()
catalog_name = config["catalog_name"]
schema_name = config["schema_name"]

# Load table configs
table_config_json = json.loads(table_config)
table_name = table_config_json["name"]
assert table_name, "Please provide a table name in the table_config json"
table_configs = tablemanager.get_configs()
matches = [table_config for table_config in table_configs if table_config.get("name") == table_name]
assert len(matches) == 1, f"Expect exactly 1 config for table `{table_name}`. Found {len(matches)}. Please fix the config file and run configuration_job"
table_volume_path_data = tablemanager.get_table_volume_path(table_name)
assert tablemanager.has_data_file(table_name), f"No data file found in {table_volume_path_data}. Please upload at least 1 file."

print(f"Table Volume Path: {table_volume_path_data}")

# COMMAND ----------

import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
  reader = spark.readStream.format("cloudFiles")
  reader = tablemanager.apply_table_config(reader, table_config_json)
  reader.option("cloudFiles.schemaLocation", tmpdir)
  display(reader.load(table_volume_path_data))
