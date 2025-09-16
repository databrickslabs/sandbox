from databricks.sdk import WorkspaceClient
import argparse
import json
import logging

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("--catalog_name", type=str, required=True)
parser.add_argument("--schema_name", type=str, required=True)
parser.add_argument("--volume_path_root", type=str, required=True)
parser.add_argument("--logging_level", type=str, required=False, default="dev")
args = parser.parse_args()

catalog_name = args.catalog_name
schema_name = args.schema_name
volume_path_root = args.volume_path_root
volume_path_data = args.volume_path_root + "/data"
logging_level = logging.DEBUG if args.logging_level == "dev" else logging.INFO

# Logging
logging.basicConfig(
  level=logging_level,
  format="%(asctime)s [%(levelname)s] %(module)s - %(message)s"
)
logger = logging.getLogger(__name__)  # per-module logger

# Initialize workspace client
ws = WorkspaceClient()

# Set property to schema
logger.info(f"Setting property to schema {catalog_name}.{schema_name}")
logger.debug(f"Volume path root: {volume_path_root}")
logger.debug(f"Volume path data: {volume_path_data}")
ws.schemas.update(full_name=f"{catalog_name}.{schema_name}", properties={
  "filepush.volume_path_root": volume_path_root,
  "filepush.volume_path_data": volume_path_data
})
logger.info(f"Schema {catalog_name}.{schema_name} configured")

# Initialize volume folder structure
logger.info(f"Initializing volume folder structure {volume_path_root}")
logger.debug(f"Creating data directory {volume_path_data}")
ws.files.create_directory(volume_path_data)
with open("../configs/tables.json", "r") as f:
  for table in json.load(f):
    table_volume_path_data = f"{volume_path_data}/{table['name']}"
    logger.debug(f"Creating table directory {table_volume_path_data}")
    ws.files.create_directory(table_volume_path_data)
logger.info(f"Volume {volume_path_root} configured")

# Dump configs to environment json
with open("../configs/environment.json", "w") as f:
  json.dump({
    "catalog_name": catalog_name,
    "schema_name": schema_name,
    "volume_path_root": volume_path_root,
    "volume_path_data": volume_path_data
  }, f)
