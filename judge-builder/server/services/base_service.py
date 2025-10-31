"""Base service class with shared authentication and MLflow setup."""

import os
import logging

import mlflow
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

# Module-level shared client
_shared_mlflow_client = None


def get_shared_mlflow_client():
    """Get the shared MLflow client instance."""
    global _shared_mlflow_client
    
    if _shared_mlflow_client is None:
        # Load env and validate auth
        load_dotenv('.env.local')
        _validate_auth()
            
        # Setup MLflow once
        mlflow.set_tracking_uri('databricks')
        _shared_mlflow_client = MlflowClient()
        
    return _shared_mlflow_client


def _validate_auth():
    """Validate Databricks authentication credentials."""
    databricks_host = os.getenv('DATABRICKS_HOST')
    databricks_token = os.getenv('DATABRICKS_TOKEN')
    databricks_client_id = os.getenv('DATABRICKS_CLIENT_ID')
    databricks_client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')

    has_token_auth = databricks_host and databricks_token
    has_oauth_auth = databricks_host and databricks_client_id and databricks_client_secret

    if not (has_token_auth or has_oauth_auth):
        # Don't fail here, just surface a potential issue
        logger.error(
            'Databricks authentication required: Set DATABRICKS_HOST and '
            '(DATABRICKS_TOKEN or DATABRICKS_CLIENT_ID+DATABRICKS_CLIENT_SECRET)'
        )


class BaseService:
    """Base service class with shared MLflow client."""

    def __init__(self):
        # Use shared client instead of creating individual instances
        self.client = get_shared_mlflow_client()
