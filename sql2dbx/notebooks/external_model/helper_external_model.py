# Databricks notebook source
# MAGIC %md
# MAGIC # Helper Notebook for External Model
# MAGIC This notebook contains utility functions for the management of secrets and external models.

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install mlflow==2.*
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,External Model Helper Functions
from typing import Any, Dict, Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import DatabricksError
from mlflow.deployments import DatabricksDeploymentClient
from requests.exceptions import HTTPError


class DatabricksSecretHelper:
    """Manages secret scopes and secrets in Databricks."""

    def __init__(self) -> None:
        """Initialize the DatabricksSecretHelper."""
        self.client = WorkspaceClient()

    def create_scope_if_not_exists(self, scope_name: str) -> None:
        """
        Create a scope if it doesn't exist.

        :param scope_name: Name of the scope to create or check
        """
        existing_scopes = [scope.name for scope in self.client.secrets.list_scopes()]
        if scope_name not in existing_scopes:
            self.client.secrets.create_scope(scope_name)
            print(f"Scope '{scope_name}' created.")
        else:
            print(f"Scope '{scope_name}' already exists.")

    def create_secret_if_not_exists(self, scope_name: str, secret_key: str, secret_value: str) -> None:
        """
        Create a secret if it doesn't exist.

        :param scope_name: Name of the scope to store the secret
        :param secret_key: Key of the secret
        :param secret_value: Value of the secret
        """
        try:
            self.client.secrets.get_secret(scope_name, secret_key)
            print(f"Secret '{secret_key}' already exists in scope '{scope_name}'.")
        except DatabricksError as e:
            error_message = str(e)
            if "Failed to get secret" in error_message and "for scope" in error_message:
                try:
                    self.client.secrets.put_secret(scope_name, secret_key, string_value=secret_value)
                    print(f"Secret '{secret_key}' created in scope '{scope_name}'.")
                except DatabricksError as put_error:
                    print(f"Failed to create secret '{secret_key}' in scope '{scope_name}': {str(put_error)}")
                    raise
            else:
                print(f"Unexpected error accessing secret '{secret_key}' in scope '{scope_name}': {error_message}")
                raise


class ExternalModelEndpointHelper:
    """Manages the creation and update of Databricks external model endpoints."""

    def __init__(self):
        """Initialize the ExternalModelEndpointHelper."""
        self.client = DatabricksDeploymentClient("databricks")

    def create_or_update_endpoint(self, endpoint_name: str, endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new endpoint or update an existing one with the given configuration.

        :param endpoint_name: Name of the endpoint to create or update
        :param endpoint_config: Configuration for the endpoint
        :return: The created or updated endpoint
        """
        try:
            existing_endpoint = self.client.get_endpoint(endpoint_name)
            endpoint = self.client.update_endpoint(endpoint=endpoint_name, config=endpoint_config)
            print(f"Endpoint '{endpoint_name}' has been successfully updated.")
        except HTTPError as e:
            if e.response.status_code == 404 and "RESOURCE_DOES_NOT_EXIST" in str(e):
                endpoint = self.client.create_endpoint(name=endpoint_name, config=endpoint_config)
                print(f"Endpoint '{endpoint_name}' has been successfully created.")
            else:
                print(f"An error occurred while getting, creating, or updating the endpoint: {str(e)}")
                raise
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            raise
        return endpoint
