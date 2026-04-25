"""
Multi-Agent Registry API - FastAPI Application

This is the main FastAPI application that provides CRUD endpoints for:
- Apps: Databricks Apps metadata
- MCP Servers: MCP server configurations
- Tools: Individual tools/functions from MCP servers
- Collections: Curated collections of tools
- Discovery: MCP catalog discovery (stub for Phase 2.2)
"""

import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings

# Export Databricks env vars so the SDK's WorkspaceClient() can find them.
# pydantic-settings reads .env into the Settings object but doesn't set os.environ.
for _attr, _env in [
    ("databricks_host", "DATABRICKS_HOST"),
    ("databricks_token", "DATABRICKS_TOKEN"),
    ("databricks_config_profile", "DATABRICKS_CONFIG_PROFILE"),
]:
    _val = getattr(settings, _attr, None)
    if _val and _env not in os.environ:
        os.environ[_env] = _val

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
from app.routes import health, apps, mcp_servers, tools, collections, discovery, supervisors, agents, admin, chat, supervisor_runtime, agent_chat, traces, a2a, catalog_assets, workspace_assets, search, lineage, audit_log, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    Initializes database tables for SQLite (dev) on startup.
    """
    from app.database import init_db, get_db
    init_db()

    # Initialize MLflow tracing (graceful degradation if unavailable)
    try:
        import mlflow
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        logger.info("MLflow tracing initialized: uri=%s experiment=%s",
                     settings.mlflow_tracking_uri, settings.mlflow_experiment_name)
    except Exception as e:
        logger.warning("MLflow initialization failed (tracing disabled): %s", e)

    # Initialize warehouse schema if using warehouse backend
    logger.info(f"[STARTUP] DATABASE_URL={settings.database_url}")
    if settings.database_url.startswith("databricks://"):
        logger.info("[STARTUP] Initializing warehouse schema")
        try:
            from app.init_warehouse_schema import init_warehouse_tables
            init_warehouse_tables()
            logger.info("[STARTUP] Warehouse schema initialization complete")
        except Exception as e:
            logger.error("[STARTUP] Warehouse schema initialization failed: %s", e, exc_info=True)
            # Don't fail startup, but discovery will likely fail without tables
    else:
        logger.info(f"[STARTUP] Skipping warehouse init (using {settings.database_url})")

    # Run auto-discovery on startup to populate database
    logger.info("[STARTUP] Running auto-discovery to populate database")
    try:
        from app.services.discovery import DiscoveryService
        import asyncio

        service = DiscoveryService()

        # Run workspace and agent discovery
        discovery_result = await service.discover_all(
            custom_urls=None,
            profile=None,  # Will use default profile or service principal auth
        )
        agent_result = await service.discover_agents_all(profile=None)

        # Upsert results
        apps_discovered = len(getattr(service, "_pending_apps", []))
        upsert_result = service.upsert_discovery_results(discovery_result)
        agent_upsert = service.upsert_agent_discovery_results(agent_result) if agent_result else None

        logger.info(
            "[STARTUP] Auto-discovery completed: %d apps, %d servers, %d tools, %d agents",
            apps_discovered,
            discovery_result.servers_discovered,
            discovery_result.tools_discovered,
            len(agent_result.agents) if agent_result else 0,
        )

    except Exception as e:
        logger.error("[STARTUP] Auto-discovery failed: %s", e, exc_info=True)
        # Don't fail the app startup if discovery fails

    yield
    # Shutdown: Clean up resources (if needed)


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    Multi-Agent Registry API for managing Databricks Apps, MCP servers, and tools.

    ## Features

    - **Apps**: Manage Databricks Apps metadata
    - **MCP Servers**: Manage MCP server configurations
    - **Tools**: Browse available tools from MCP servers
    - **Collections**: Create curated collections of apps, servers, and tools
    - **Discovery**: Automatic discovery of apps and tools from Databricks workspace

    ## Authentication

    This API uses On-Behalf-Of (OBO) authentication via Databricks Unity Catalog.
    Each request is executed with the caller's identity for proper governance.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware (must be added LAST so it runs FIRST and adds headers to all responses)
# Parse origins from environment variable, defaulting to webapp URL
cors_origins_list = settings.cors_origins.split(",")
# Ensure webapp URL is included
webapp_url = "https://multi-agent-registry-webapp-7474660127789418.aws.databricksapps.com"
if webapp_url not in cors_origins_list:
    cors_origins_list.append(webapp_url)

logger.info(f"CORS configured with origins: {cors_origins_list}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods.split(","),
    allow_headers=settings.cors_headers.split(","),
    expose_headers=["*"],  # Expose all headers to the client
)

# Authentication Middleware (added after CORS so it runs second)
from app.middleware.auth import DatabricksAuthMiddleware
if settings.auth_enabled:
    app.add_middleware(DatabricksAuthMiddleware)


# Exception Handlers


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422).
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all exceptions including Databricks SQL errors (500).
    """
    # Check if this is a databricks-sql error
    exc_module = type(exc).__module__
    if "databricks" in exc_module or "sql" in exc_module:
        logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Database error occurred",
                "error": str(exc) if settings.debug else "Internal server error",
            },
        )

    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Include Routers

# Health check endpoints (no prefix)
app.include_router(health.router)

# API endpoints with prefix
app.include_router(apps.router, prefix=settings.api_prefix)
app.include_router(mcp_servers.router, prefix=settings.api_prefix)
app.include_router(tools.router, prefix=settings.api_prefix)
app.include_router(collections.router, prefix=settings.api_prefix)
app.include_router(discovery.router, prefix=settings.api_prefix)
app.include_router(supervisors.router, prefix=settings.api_prefix)
app.include_router(supervisor_runtime.router, prefix=settings.api_prefix)
# Also mount at /supervisor for webapp compatibility (webapp expects /supervisor/chat)
app.include_router(supervisor_runtime.router, prefix="/supervisor")
app.include_router(agents.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(agent_chat.router, prefix=settings.api_prefix)
app.include_router(traces.router, prefix=settings.api_prefix)
app.include_router(a2a.router, prefix=settings.api_prefix)
app.include_router(catalog_assets.router, prefix=settings.api_prefix)
app.include_router(workspace_assets.router, prefix=settings.api_prefix)
app.include_router(search.router, prefix=settings.api_prefix)
app.include_router(lineage.router, prefix=settings.api_prefix)
app.include_router(audit_log.router, prefix=settings.api_prefix)
app.include_router(conversations.router, prefix=settings.api_prefix)


# Static files for React frontend
WEBAPP_DIST = Path(__file__).parent.parent / "webapp_dist"
if WEBAPP_DIST.exists():
    # Mount static assets (JS, CSS, images) with caching
    # These have hashed filenames (index-xyz123.js) so can be cached forever
    app.mount("/assets", StaticFiles(directory=WEBAPP_DIST / "assets"), name="assets")

    # Serve React app for known React Router paths
    @app.get("/", include_in_schema=False)
    @app.get("/discover", include_in_schema=False)
    @app.get("/collections", include_in_schema=False)
    @app.get("/chat", include_in_schema=False)
    @app.get("/agents", include_in_schema=False)
    @app.get("/agent-chat", include_in_schema=False)
    @app.get("/lineage", include_in_schema=False)
    @app.get("/audit-log", include_in_schema=False)
    async def serve_react_app():
        """
        Serve React app index.html for client-side routing.
        Set no-cache headers so users always get the latest version.
        """
        response = FileResponse(WEBAPP_DIST / "index.html")
        # Prevent caching of the HTML file so users always get latest version
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
else:
    # Webapp not built, show API info at root
    @app.get("/", tags=["Root"])
    def root():
        """API information."""
        return {
            "name": settings.api_title,
            "version": settings.api_version,
            "docs": "/docs",
            "health": "/health",
            "api": settings.api_prefix,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
