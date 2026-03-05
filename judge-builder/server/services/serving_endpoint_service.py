"""Service for managing Databricks serving endpoints."""

import logging
from typing import List

from cachetools import TTLCache
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServingEndpoint

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ServingEndpointService(BaseService):
    """Handles serving endpoint operations with caching."""

    def __init__(self):
        super().__init__()
        self.workspace_client = WorkspaceClient()
        # Cache endpoints for 5 minutes (300 seconds)
        self._endpoints_cache = TTLCache(maxsize=1, ttl=300)
        self._CACHE_KEY = "endpoints_list"

    def list_serving_endpoints(self, force_refresh: bool = False) -> List[ServingEndpoint]:
        """List all serving endpoints in the workspace with caching.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of serving endpoints
        """
        if not force_refresh and self._CACHE_KEY in self._endpoints_cache:
            logger.info("Returning cached serving endpoints")
            return self._endpoints_cache[self._CACHE_KEY]

        try:
            endpoints = list(self.workspace_client.serving_endpoints.list())
            logger.info(f"Retrieved {len(endpoints)} serving endpoints")
            self._endpoints_cache[self._CACHE_KEY] = endpoints
            return endpoints
        except Exception as e:
            logger.error(f"Failed to list serving endpoints: {e}")
            raise

    def get_endpoint(self, name: str) -> ServingEndpoint:
        """Get details for a specific serving endpoint.

        This supports both cached endpoints and manually entered names.

        Args:
            name: Endpoint name

        Returns:
            ServingEndpoint object
        """
        try:
            endpoint = self.workspace_client.serving_endpoints.get(name)
            logger.info(f"Retrieved endpoint: {name}")
            return endpoint
        except Exception as e:
            logger.error(f"Failed to get endpoint {name}: {e}")
            raise

    def validate_endpoint_name(self, name: str) -> bool:
        """Validate that an endpoint name exists.

        Useful for manually entered endpoint names.

        Args:
            name: Endpoint name to validate

        Returns:
            True if endpoint exists, False otherwise
        """
        try:
            self.get_endpoint(name)
            return True
        except Exception:
            return False


# Global service instance
serving_endpoint_service = ServingEndpointService()
