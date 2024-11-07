import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import BadRequest
from databricks.labs.blueprint.tui import Prompts
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk.service.catalog import VolumeType
from databricks.sdk.errors import PermissionDenied
import os

"""
Approach

User first sets all configuration options
validate options
validate user permissions
then create infra
upload app file to databricks

"""


class UnityCatalogInfra:
    def __init__(
        self,
        config,
        workspace_client: WorkspaceClient,
        p: Prompts,
        see: StatementExecutionExt,
    ):
        self.w = workspace_client
        self.config = config
        self.prompts = p
        self.see = see

        # these are updated as the user makes a choice about which UC catalog and schema to use.
        # the chosen values are then written back into the config file.
        self.migration_assistant_UC_catalog = None
        self.migration_assistant_UC_schema = "sql_migration_assistant"

        # user cannot change these values
        self.tables = {
            "code_intent" : f"(id BIGINT, code STRING, intent STRING) TBLPROPERTIES (delta.enableChangeDataFeed = true)",
            "prompt_history" : f"(id BIGINT GENERATED ALWAYS AS IDENTITY, agent STRING, prompt STRING, temperature DOUBLE, token_limit INT, save_time TIMESTAMP)",
        }
        self.volume_name = "sql_migration_assistant_volume"
        self.volume_dirs = {
            "checkpoint": "code_ingestion_checkpoints",
            "input": "input_code",
            "output": "output_code",
        }
        self.warehouseID = self.config.get("DATABRICKS_WAREHOUSE_ID")

        # add values to config
        self.config["CODE_INTENT_TABLE_NAME"] = "code_intent"
        self.config["PROMPT_HISTORY_TABLE_NAME"] = "prompt_history"

    def choose_UC_catalog(self):
        """Ask the user to choose an existing Unity Catalog or create a new one."""
        # TODO - check user permissions to create a catalog
        # metastore= self.w.metastore.current()
        # metastore_grants = self.w.grants.get_effective(SecurableType.CATALOG, metastore.metastore_id)
        # w.grants.get_effective(SecurableType.SCHEMA, "robert_whiffin.migration_assistant")

        catalogs = [x.name for x in self.w.catalogs.list()]
        # Create a list of all catalogs in the workspace. Returns a generator

        question = "Choose a catalog:"
        choice = self.prompts.choice(question, catalogs)

        self.migration_assistant_UC_catalog = choice
        # update config with user choice
        self.config["CATALOG"] = self.migration_assistant_UC_catalog

    def create_schema(self):

        # update config with user choice
        self.config["SCHEMA"] = self.migration_assistant_UC_schema
        try:
            self._create_UC_schema()
            self._create_UC_volume(self.migration_assistant_UC_schema)
        except BadRequest as e:
            if "already exists" in str(e):
                print(
                    f"Schema already exists. Using existing schema {self.migration_assistant_UC_schema}."
                )
                self._create_UC_volume(self.migration_assistant_UC_schema)

    def _create_UC_catalog(self):
        """Create a new Unity Catalog."""
        self.w.catalogs.create(
            name=self.migration_assistant_UC_catalog,
            comment="Catalog for storing assets related to the SQL migration assistant.",
        )

    def _create_UC_schema(self):
        """Create a new Unity Schema."""
        self.w.schemas.create(
            name=self.migration_assistant_UC_schema,
            catalog_name=self.migration_assistant_UC_catalog,
            comment="Schema for storing assets related to the SQL migration assistant.",
        )

    def _create_UC_volume(self, schema):
        try:
            self.w.volumes.create(
                name=self.volume_name,
                catalog_name=self.migration_assistant_UC_catalog,
                schema_name=schema,
                comment="Volume for storing assets related to the SQL migration assistant.",
                volume_type=VolumeType.MANAGED,
            )
            for key in self.volume_dirs.keys():
                dir_ = self.volume_dirs[key]
                volume_path = f"/Volumes/{self.migration_assistant_UC_catalog}/{schema}/{self.volume_name}/{dir_}"
                self.w.dbutils.fs.mkdirs(volume_path)
                self.config[f"VOLUME_NAME_{key.upper()}_PATH"] = volume_path
            self.config["VOLUME_NAME"] = self.volume_name
        except PermissionDenied:
            print(
                "You do not have permission to create a volume. A volume will not be created. You will need to create a "
                "volume to run the batch code transformation process."
            )
            logging.error(
                "You do not have permission to create a volume. A volume will not be created. You will need to create a "
                "volume to run the batch code transformation process."
            )

    def create_tables(self):
        """Create a new table to store code intent data."""

        for table_name, table_spec in self.tables.items():
            _ = self.see.execute(
                statement=f"CREATE TABLE IF NOT EXISTS `{table_name}` {table_spec}",
                catalog=self.migration_assistant_UC_catalog,
                schema=self.migration_assistant_UC_schema,
            )
