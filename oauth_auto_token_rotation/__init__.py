"""
Databricks OAuth Auto Token Rotation

Automatic OAuth token rotation for Databricks PostgreSQL (Lakebase) and other services.
Eliminates the need for manual token updates by running as a background service.
"""

__version__ = "1.0.0"
__author__ = "Databricks Community"
__license__ = "Apache-2.0"

from .rotator import DatabricksOAuthRotator

__all__ = ["DatabricksOAuthRotator"]
