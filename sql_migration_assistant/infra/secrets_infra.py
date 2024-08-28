import logging

from databricks.sdk import WorkspaceClient
from databricks.labs.blueprint.tui import Prompts

class SecretsInfra():
    def __init__(self, config, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.config = config
        self.prompts = Prompts()
        self.pat_key = "sql-migration-pat"
    def create_secret_PAT(self):
        logging.info("Creating a Databricks PAT for the SQL Migration Assistant")
        scopes = self.w.secrets.list_scopes()
        question = ("Choose a scope to create the secret in:")
        _ = [scope.name for scope in scopes]
        scope_name = self.prompts.choice(question, _)


        # create the PAT
        logging.info("Creating a Databricks PAT")
        pat_response = self.w.tokens.create(
            comment='sql_migration_assistant',
        )
        pat = pat_response.token_value

        logging.info(f"Storing the PAT in scope {scope_name} under key {self.pat_key}")
        # store pat in scope
        self.w.secrets.put_secret(
            scope=scope_name,
            key='sql-migration-pat',
            string_value=pat
        )

        # save user choice in config
        self.config["DATABRICKS_TOKEN_SECRET_SCOPE"] = scope_name
        self.config["DATABRICKS_TOKEN_SECRET_KEY"] = self.pat_key
        self.config["DATABRICKS_HOST"] = self.w.config.host