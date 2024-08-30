from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import BadRequest
from databricks.labs.blueprint.tui import Prompts
from databricks.labs.lsql.core import StatementExecutionExt
import logging
import time

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

        # get defaults from config file
        self.default_UC_catalog = "sql_migration_assistant"
        self.default_UC_schema = "sql_migration_assistant"

        # these are updated as the user makes a choice about which UC catalog and schema to use.
        # the chosen values are then written back into the config file.
        self.migration_assistant_UC_catalog = None
        self.migration_assistant_UC_schema = None

        # user cannot change these values
        self.code_intent_table_name = "sql_migration_assistant_code_intent_table"
        self.warehouseID = self.config.get("DATABRICKS_WAREHOUSE_ID")

        # add code intent table name to config
        self.config["CODE_INTENT_TABLE_NAME"] = self.code_intent_table_name

    def choose_UC_catalog(self):
        """Ask the user to choose an existing Unity Catalog or create a new one."""
        # TODO - check user permissions to create a catalog
        # metastore= self.w.metastore.current()
        # metastore_grants = self.w.grants.get_effective(SecurableType.CATALOG, metastore.metastore_id)
        # w.grants.get_effective(SecurableType.SCHEMA, "robert_whiffin.migration_assistant")

        catalogs = [f"CREATE NEW CATALOG: {self.default_UC_catalog}"]
        # Create a list of all catalogs in the workspace. Returns a generator
        catalogs.extend([x.name for x in self.w.catalogs.list()])

        question = "Choose a catalog:"
        choice = self.prompts.choice(question, catalogs)
        if choice == f"CREATE NEW CATALOG: {self.default_UC_catalog}":
            self.migration_assistant_UC_catalog = self.default_UC_catalog
            logging.info(
                f"Creating new UC catalog {self.migration_assistant_UC_catalog}."
            )
            print(f"Creating new UC catalog {self.migration_assistant_UC_catalog}.")
            self._create_UC_catalog()
        else:
            self.migration_assistant_UC_catalog = choice
            # update config with user choice
            self.config["CATALOG"] = self.migration_assistant_UC_catalog

    def choose_schema_name(self):

        use_default_schema_name = self.prompts.confirm(
            f"Would you like to use the default schema name: {self.default_UC_schema}? (yes/no)"
        )
        if use_default_schema_name:
            self.migration_assistant_UC_schema = self.default_UC_schema
        else:
            # Ask the user to enter a schema name, and validate it.
            name_invalid = True
            while name_invalid:
                # Name cannot include period, space, or forward-slash
                schema_name = self.prompts.question("Enter the schema name: ")
                if (
                    "." not in schema_name
                    and " " not in schema_name
                    and "/" not in schema_name
                ):
                    self.migration_assistant_UC_schema = schema_name
                    name_invalid = False
                else:
                    print("Schema name cannot include period, space, or forward-slash.")
        # update config with user choice
        self.config["SCHEMA"] = self.migration_assistant_UC_schema
        try:
            self._create_UC_schema()
        except BadRequest as e:
            if "already exists" in str(e):
                print(
                    f"Schema already exists. Using existing schema {self.migration_assistant_UC_schema}."
                )

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

    def create_code_intent_table(self):
        """Create a new table to store code intent data."""

        table_name = self.code_intent_table_name

        _ = self.see.execute(
            f"CREATE TABLE IF NOT EXISTS "
            f"`{self.migration_assistant_UC_catalog}.{self.migration_assistant_UC_schema}.{table_name}`"
            f" (id BIGINT, code STRING, intent STRING) "
            f"TBLPROPERTIES (delta.enableChangeDataFeed = true)",
        )

