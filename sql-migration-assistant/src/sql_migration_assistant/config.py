import os

FOUNDATION_MODEL_NAME = os.environ.get("SERVED_FOUNDATION_MODEL_NAME")
SQL_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
VECTOR_SEARCH_ENDPOINT_NAME = os.environ.get("VECTOR_SEARCH_ENDPOINT_NAME")
VS_INDEX_NAME = os.environ.get("VS_INDEX_NAME")
CODE_INTENT_TABLE_NAME = os.environ.get("CODE_INTENT_TABLE_NAME")
CATALOG = os.environ.get("CATALOG")
SCHEMA = os.environ.get("SCHEMA")
VOLUME_NAME = os.environ.get("VOLUME_NAME")
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
TRANSFORMATION_JOB_ID = os.environ.get("TRANSFORMATION_JOB_ID")
WORKSPACE_LOCATION = os.environ.get("WORKSPACE_LOCATION")
VOLUME_NAME_INPUT_PATH = os.environ.get("VOLUME_NAME_INPUT_PATH")
PROMPT_HISTORY_TABLE_NAME = os.environ.get("PROMPT_HISTORY_TABLE_NAME")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")