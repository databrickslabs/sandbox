"""
This code is called after the user has run through the configutation steps in initialsetup.py.
This uploads the config, runindatabricks.py, and gradio_app.py files to the Databricks workspace.
"""

from databricks.labs.blueprint.installation import Installation
from databricks.sdk import WorkspaceClient
from dataclasses import make_dataclass
import os


class FileUploader:
    def __init__(self, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.installer = Installation(self.w, "sql_migration_assistant")

    def upload(
        self,
        file_name,
    ):
        with open(file_name, "rb") as file:
            contents = file.read()
            self.installer.upload(file_name, contents)

    def save_config(self, config):
        X = make_dataclass("X", fields=config.keys())

        config_class = X(**config)

        self.installer.save(config_class, filename="config.yml")
