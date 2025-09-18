import os
import json
from . import envmanager
from . import formatmanager
from pyspark.sql.streaming import DataStreamReader
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import NotFound

def get_table_volume_path(table_name: str) -> str:
  ws = WorkspaceClient()
  table_volume_path_data = os.path.join(envmanager.get_config()["volume_path_data"], table_name)
  try:
    ws.files.get_directory_metadata(table_volume_path_data)
  except NotFound:
    raise RuntimeError(f"Table data path not found for table `{table_name}`. Have you run `databricks bundle run configuration_job`?")
  return table_volume_path_data

def has_data_file(table_name: str) -> bool:
  ws = WorkspaceClient()
  table_volume_path_data = get_table_volume_path(table_name)
  try:
    iter = ws.files.list_directory_contents(table_volume_path_data)
    next(iter)
  except StopIteration:
    return False
  return True

def is_table_created(table_name: str) -> bool:
  ws = WorkspaceClient()
  return ws.tables.exists(full_name=f"{envmanager.get_config()['catalog_name']}.{envmanager.get_config()['schema_name']}.{table_name}").table_exists

def get_configs() -> list:
  json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "tables.json")
  if not os.path.exists(json_path):
    raise RuntimeError(f"Missing table configs file: {json_path}. Please following README.md to create one, deploy and run configuration_job.")
  with open(json_path, "r") as f:
    configs = json.load(f)
  return configs

def apply_table_config(reader: DataStreamReader, table_config: dict) -> DataStreamReader:
  fmt = table_config.get("format")
  if fmt is None:
    raise ValueError(f"format is required for table {table_config.get('name')}")

  # format-specific options from user input
  user_fmt_opts = table_config.get("format_options", {})
  # validate and get the final modified options
  final_fmt_opts = formatmanager.get_format_manager(fmt).get_merged_options(user_fmt_opts)

  reader = reader.format("cloudFiles").option("cloudFiles.format", fmt)
  for k, v in final_fmt_opts.items():
    reader = reader.option(k, v)
  
  # schema hints
  schema_hints = table_config.get("schema_hints")
  if schema_hints:
    reader = reader.option("cloudFiles.schemaHints", schema_hints)

  return reader
  