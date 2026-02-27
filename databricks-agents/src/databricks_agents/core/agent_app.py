"""
Core AgentApp class that wraps FastAPI to create discoverable agents.

This is the main entry point for building agent-enabled Databricks Apps.
"""

import inspect
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


def _python_type_to_json_schema(annotation) -> str:
    """Convert a Python type annotation to a JSON Schema type string.

    Handles generics like ``List[str]``, ``Optional[int]``,
    ``Dict[str, Any]``, as well as plain types like ``str``, ``int``.
    """
    if annotation is inspect.Parameter.empty:
        return "string"

    origin = get_origin(annotation)

    # Optional[X] → unwrap to X
    if origin is type(None):
        return "string"

    # typing.Union / Optional comes through as Union
    # Optional[int] == Union[int, None]
    import typing
    if origin is getattr(typing, "Union", None):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return _python_type_to_json_schema(args[0])
        return "string"

    if origin is list or origin is List:
        return "array"
    if origin is dict or origin is Dict:
        return "object"
    if origin is set or origin is frozenset:
        return "array"
    if origin is tuple:
        return "array"

    # Plain types
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        bytes: "string",
    }
    return type_map.get(annotation, "string")


class ToolDefinition(BaseModel):
    """Definition of an agent tool (function callable via MCP)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class AgentMetadata(BaseModel):
    """Agent metadata for A2A protocol."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    capabilities: List[str]
    version: str = "1.0.0"
    protocol_version: str = "a2a/1.0"
    tools: List[ToolDefinition] = []


class AgentApp(FastAPI):
    """
    FastAPI wrapper that adds agent capabilities.

    Usage:
        app = AgentApp(
            name="my_agent",
            description="Does something useful",
            capabilities=["search", "analysis"]
        )

        @app.tool(description="Search for items")
        async def search(query: str) -> dict:
            return {"results": [...]}
    """

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: List[str],
        uc_catalog: Optional[str] = None,
        uc_schema: Optional[str] = None,
        auto_register: bool = True,
        enable_mcp: bool = True,
        **kwargs,
    ):
        # Build the lifespan context manager before calling super().__init__
        # so FastAPI uses it instead of deprecated on_event("startup").
        user_lifespan = kwargs.pop("lifespan", None)
        agent_self = self  # capture for closure

        @asynccontextmanager
        async def _lifespan(app):
            # --- startup ---
            if agent_self.auto_register:
                await agent_self._register_in_uc()
            if user_lifespan:
                async with user_lifespan(app) as state:
                    yield state
            else:
                yield
            # --- shutdown (nothing needed currently) ---

        super().__init__(lifespan=_lifespan, **kwargs)

        self.agent_metadata = AgentMetadata(
            name=name,
            description=description,
            capabilities=capabilities,
        )

        self.uc_catalog = uc_catalog or os.getenv("UC_CATALOG", "main")
        self.uc_schema = uc_schema or os.getenv("UC_SCHEMA", "agents")
        self.auto_register = auto_register
        self.enable_mcp = enable_mcp

        # Set up standard agent endpoints
        self._setup_agent_endpoints()

        # Set up MCP server if enabled
        if self.enable_mcp:
            self._setup_mcp_server()

    def _setup_agent_endpoints(self):
        """Set up standard A2A protocol endpoints."""

        @self.get("/.well-known/agent.json")
        async def agent_card():
            """A2A protocol agent card."""
            return {
                "schema_version": self.agent_metadata.protocol_version,
                "name": self.agent_metadata.name,
                "description": self.agent_metadata.description,
                "capabilities": self.agent_metadata.capabilities,
                "version": self.agent_metadata.version,
                "endpoints": {
                    "mcp": "/api/mcp",
                    "invoke": "/api/invoke",
                },
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                    for tool in self.agent_metadata.tools
                ],
            }

        @self.get("/.well-known/openid-configuration")
        async def openid_config():
            """Delegate authentication to workspace OIDC."""
            databricks_host = os.getenv("DATABRICKS_HOST", "")
            if databricks_host and not databricks_host.startswith("http"):
                databricks_host = f"https://{databricks_host}"

            return {
                "issuer": f"{databricks_host}/oidc",
                "authorization_endpoint": f"{databricks_host}/oidc/oauth2/v2.0/authorize",
                "token_endpoint": f"{databricks_host}/oidc/v1/token",
                "jwks_uri": f"{databricks_host}/oidc/v1/keys",
            }

        @self.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "agent": self.agent_metadata.name,
                "version": self.agent_metadata.version,
            }

    def tool(
        self,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator to register a function as an agent tool.

        Usage:
            @app.tool(description="Search the database")
            async def search(query: str) -> dict:
                return {...}
        """

        def decorator(func: Callable):
            sig = inspect.signature(func)

            if parameters is None:
                param_schema = {}
                for pname, param in sig.parameters.items():
                    param_schema[pname] = {
                        "type": _python_type_to_json_schema(param.annotation),
                        "required": param.default == inspect.Parameter.empty,
                    }
            else:
                param_schema = parameters

            tool_def = ToolDefinition(
                name=func.__name__,
                description=description,
                parameters=param_schema,
                function=func,
            )
            self.agent_metadata.tools.append(tool_def)

            # Register as FastAPI endpoint
            self.post(f"/api/tools/{func.__name__}")(func)

            return func

        return decorator

    async def _register_in_uc(self):
        """Register agent in Unity Catalog on app startup."""
        try:
            from ..registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError

            app_url = os.getenv("DATABRICKS_APP_URL")
            if not app_url:
                logger.debug("DATABRICKS_APP_URL not set — skipping UC registration")
                return

            registry = UCAgentRegistry()

            spec = UCAgentSpec(
                name=self.agent_metadata.name,
                catalog=self.uc_catalog,
                schema=self.uc_schema,
                endpoint_url=app_url,
                description=self.agent_metadata.description,
                capabilities=self.agent_metadata.capabilities,
                properties={
                    "protocol_version": self.agent_metadata.protocol_version,
                    "version": self.agent_metadata.version,
                },
            )

            result = registry.register_agent(spec)
            logger.info(
                "Registered agent in UC: %s (catalog=%s, schema=%s)",
                result["full_name"],
                self.uc_catalog,
                self.uc_schema,
            )

        except UCRegistrationError as e:
            logger.warning(
                "UC registration failed for %s.%s.%s: %s — "
                "check that the catalog and schema exist and you have CREATE MODEL permission",
                self.uc_catalog,
                self.uc_schema,
                self.agent_metadata.name,
                e,
            )
        except Exception as e:
            logger.warning("UC registration error: %s", e)

    def _setup_mcp_server(self):
        """Set up MCP server endpoints."""
        try:
            from ..mcp import MCPServerConfig, setup_mcp_server

            config = MCPServerConfig(
                name=self.agent_metadata.name,
                description=self.agent_metadata.description,
                version=self.agent_metadata.version,
            )

            setup_mcp_server(self, config)
            logger.info("MCP server enabled at /api/mcp")

        except Exception as e:
            logger.warning("MCP server setup failed: %s", e)
