"""Authentication and request middleware for the registry API."""

from app.middleware.auth import DatabricksAuthMiddleware

__all__ = ["DatabricksAuthMiddleware"]
