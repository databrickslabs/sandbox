"""
Databricks Apps OBO (On-Behalf-Of) authentication middleware.

When deployed on Databricks Apps, the platform proxy injects user identity
headers (X-Forwarded-Email, X-Forwarded-User, X-Forwarded-Access-Token)
into every request. This middleware enforces that those headers are present
for all API endpoints, while leaving health/docs endpoints open.

In local development (DEBUG=true), authentication is skipped entirely.
"""

import logging

from fastapi import Request, HTTPException, status as http_status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

OPEN_PATHS = {
    "/health", "/ready", "/debug-db", "/docs", "/redoc", "/openapi.json",
    # Discovery/registry read-only endpoints - public for frontend access
    "/api/apps", "/api/agents", "/api/collections", "/api/tools",
    "/api/mcp-servers", "/api/catalog-assets", "/api/workspace-assets",
    "/api/discovery", "/api/search",
}


class DatabricksAuthMiddleware(BaseHTTPMiddleware):
    """Validates Databricks Apps platform headers on non-open endpoints."""

    async def dispatch(self, request: Request, call_next):
        # Always allow health, docs, and schema endpoints
        if any(request.url.path.startswith(p) for p in OPEN_PATHS):
            return await call_next(request)

        # Allow all /api/* GET requests (read-only discovery)
        if request.url.path.startswith("/api/") and request.method == "GET":
            return await call_next(request)

        # Skip auth in local dev mode
        if settings.debug:
            return await call_next(request)

        # Require at least one Databricks Apps identity header
        user_email = request.headers.get("X-Forwarded-Email")
        access_token = request.headers.get("X-Forwarded-Access-Token")

        if not user_email and not access_token:
            logger.warning(
                "Unauthenticated request blocked: %s %s",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        # Attach identity to request.state for downstream use
        request.state.user_email = user_email or ""
        request.state.access_token = access_token or ""
        return await call_next(request)
