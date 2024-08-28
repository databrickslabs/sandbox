from databricks.sdk import WorkspaceClient
import yaml
import os

class ConfigLoader:
    """
    This is used to make it easy to transfer variables between a notebook and a workspace file using
    environment variables.
    """
    def read_yaml_to_env(self, file_path):
        """Reads a YAML file and sets environment variables based on its contents.

        Args:
            file_path (str): The path to the YAML file.

        """
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            for key, value in data.items():
                os.environ[key] = str(value)

        w = WorkspaceClient()
        dbutils = w.dbutils

        DATABRICKS_TOKEN = dbutils.secrets.get(
            scope=os.environ.get("DATABRICKS_TOKEN_SECRET_SCOPE")
            , key=os.environ.get("DATABRICKS_TOKEN_SECRET_KEY")
            )

        os.environ['DATABRICKS_TOKEN'] = DATABRICKS_TOKEN

        # remove trailing slash from databricks host if present
        DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
        if DATABRICKS_HOST[-1] == '/':
            DATABRICKS_HOST = DATABRICKS_HOST[:-1]
            os.environ['DATABRICKS_HOST'] = DATABRICKS_HOST
