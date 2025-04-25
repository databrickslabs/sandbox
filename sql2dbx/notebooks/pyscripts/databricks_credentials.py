import os
from typing import Dict


class DatabricksCredentials:
    """
    Provides access to Databricks host and authentication token from environment variables or dbutils.

    This class handles two authentication approaches:
    1. Environment variables: DATABRICKS_HOST and DATABRICKS_TOKEN
    2. Ephemeral tokens from dbutils (when running in Databricks notebooks)

    Important: Ephemeral tokens have a short lifespan, so this class retrieves fresh values
    on each property access to ensure tokens are always valid, even after rotation.
    """

    def get_host_and_token(self) -> Dict[str, str]:
        """
        Returns both host URL and authentication token as a dictionary.

        The values are freshly retrieved each time this method is called
        to ensure token validity, as Databricks ephemeral tokens might expire quickly.

        Returns:
            Dict with 'host' and 'token' keys

        Raises:
            RuntimeError: If credentials cannot be retrieved from either source
        """
        # First check environment variables
        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")

        if host and token:
            return {"host": host, "token": token}

        # Fallback to dbutils if environment variables not found
        try:
            import IPython
            ipython = IPython.get_ipython()
            dbutils = ipython.user_ns["dbutils"]
            ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()

            # Get both values at once from the context
            return {
                "host": getattr(ctx, "apiUrl")().get(),
                "token": getattr(ctx, "apiToken")().get()
            }
        except Exception as e:
            raise RuntimeError(
                "Could not retrieve Databricks credentials from environment or dbutils context."
            ) from e

    @property
    def host(self) -> str:
        """
        Returns the current Databricks host URL.

        Note: This retrieves a fresh value on each access.

        Raises:
            RuntimeError: If the host cannot be found in environment variables or via dbutils.
        """
        return self.get_host_and_token()["host"]

    @property
    def token(self) -> str:
        """
        Returns the current Databricks authentication token.

        Note: This retrieves a fresh value on each access to ensure the token is valid,
        as Databricks ephemeral tokens have a short lifespan.

        Raises:
            RuntimeError: If the token cannot be found in environment variables or via dbutils.
        """
        return self.get_host_and_token()["token"]
