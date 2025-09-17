import os
import json
from . import envmanager
from pyspark.sql.streaming import DataStreamReader
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import NotFound

def validate_config(config: dict):
  pass

def get_table_volume_path(table_name: str) -> str:
  # Initialize workspace client
  ws = WorkspaceClient()
  table_volume_path_data = os.path.join(envmanager.get_config()["volume_path_data"], table_name)
  try:
    ws.files.get_directory_metadata(table_volume_path_data)
  except NotFound:
    assert False, f"Table data path not found for table `{table_name}`. Have you run `databricks bundle run configuration_job`?"
  return table_volume_path_data

def has_data_file(table_name: str) -> bool:
  # Initialize workspace client
  ws = WorkspaceClient()
  table_volume_path_data = get_table_volume_path(table_name)
  try:
    iter = ws.files.list_directory_contents(table_volume_path_data)
    next(iter)
  except StopIteration:
    return False
  return True

def get_configs() -> list:
  json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "tables.json")
  assert os.path.exists(json_path), f"Missing table configs file: {json_path}. Please following README.md to create one, deploy and run configuration_job." 
  with open(json_path, "r") as f:
    configs = json.load(f)
  return configs

def apply_table_config(reader: DataStreamReader, table_config: dict) -> DataStreamReader:
  fmt = table_config.get("format")
  assert fmt is not None, f"format is required for table {table_config.get('name')}"
  reader = reader.option("cloudFiles.format", fmt)

  # format-specific options
  fmt_opts = table_config.get("format_options", {})
  for k, v in fmt_opts.items():
    reader = reader.option(k, v)
  
  # schema hints
  # always have _rescued_data
  reader = reader.schema("_rescued_data STRING")
  schema_hints = table_config.get("schema_hints")
  if schema_hints:
    reader = reader.option("cloudFiles.schemaHints", schema_hints)

  return reader
  