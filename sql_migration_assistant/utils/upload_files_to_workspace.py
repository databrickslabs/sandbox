"""
This code is called after the user has run through the configutation steps in initialsetup.py.
This uploads the config, runindatabricks.py, and gradio_app_backup.py files to the Databricks workspace.
"""

from databricks.labs.blueprint.installation import Installation
from databricks.sdk import WorkspaceClient
from dataclasses import make_dataclass
import os


class FileUploader:
    def __init__(self, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.installer = Installation(ws=self.w, product="sql_migration_assistant")

    def upload(
        self,
        file_path,
        file_name,
    ):
        with open(file_path, "rb") as file:
            contents = file.read()
            self.installer.upload(file_name, contents)

    def save_config(self, config):
        # add in the Workspace location to the config
        config["WORKSPACE_LOCATION"] = self.installer._install_folder
        X = make_dataclass("X", fields=config.keys())

        config_class = X(**config)

        self.installer.save(config_class, filename="config.yml")
