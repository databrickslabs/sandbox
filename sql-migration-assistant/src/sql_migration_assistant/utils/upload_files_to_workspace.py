"""
This code is called after the user has run through the configutation steps in initialsetup.py.
This uploads the config, runindatabricks.py, and gradio_app_backup.py files to the Databricks workspace.
"""

from dataclasses import make_dataclass

from databricks.labs.blueprint.installation import Installation
from databricks.sdk import WorkspaceClient


class FileUploader:
    def __init__(self, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.installer = Installation(ws=self.w, product="sql-migration-assistant")

    def upload(
        self,
        file_path,
        file_name,
    ):
        with open(file_path, "rb") as file:
            contents = file.read()
            self.installer.upload(file_name, contents)

    def update_config(self, config):
        # add in the Workspace location to the config
        config["WORKSPACE_LOCATION"] = self.installer.install_folder()
        return config

    def save_config(self, config):
        # not used, need to get working
        X = make_dataclass("X", fields=config.keys())

        config_class = X(**config)

        self.installer.save(
            config_class, filename="src/sql_migration_assistant/config.yml"
        )
