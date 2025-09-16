# Databricks notebook source
import json
import os

# Widget
dbutils.widgets.text("table_name", "", "Table Name")

# Load configs to environment json
environment_path = "./configs/environment.json"
table_configs_path = "./configs/tables.json"

assert os.path.exists(environment_path), f"Missing environment file: {environment_path}. Have you run `databricks bundle run configuration_job`?"
assert os.path.exists(table_configs_path), f"Missing table configs file: {table_configs_path}"

with open(environment_path, "r") as f:
    configs = json.load(f)
with open(table_configs_path, "r") as f:
    table_configs = json.load(f)

catalog_name = configs["catalog_name"]
schema_name = configs["schema_name"]
table_name = dbutils.widgets.get("table_name")
assert table_name, "Please provide a table name"
table_volume_path_data = configs["volume_path_data"] + f"/{table_name}"

# Locate table config
matches = [table_config for table_config in table_configs if table_config.get("name") == table_name]
assert len(matches) == 1, f"Expect exactly 1 config for table `{table_name}`. Found {len(matches)}. Please fix the config file."
table_config = matches[0]

print(f"Table Volume Path: {table_volume_path_data}")
print(f"Table Config: {table_config}")

# COMMAND ----------

import tempfile
from utils import configmanager

with tempfile.TemporaryDirectory() as tmpdir:
    reader = spark.readStream.format("cloudFiles")
    reader = configmanager.apply_table_config(reader, table_config)
    reader.option("cloudFiles.schemaLocation", tmpdir)
    display(reader.load(table_volume_path_data))