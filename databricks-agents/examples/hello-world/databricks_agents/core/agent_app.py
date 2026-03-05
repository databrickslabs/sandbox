"""
Core AgentApp class for building discoverable agents on Databricks Apps.

AgentApp uses composition (not inheritance) with FastAPI. Register tools via
@agent.tool(), then call agent.as_fastapi() to get a fully-wired FastAPI app
with /invocations, A2A, MCP, and health endpoints.
"""

import inspect
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


def _python_type_to_json_schema(annotation) -> str:
    """Convert a Python type annotation to a JSON Schema type string."""
    if annotation is inspect.Parameter.empty:
        return "string"

    origin = get_origin(annotation)

    if origin is type(None):
        return "string"

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
    """Definition of an agent tool (function callable via MCP or /invocations)."""

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


class AgentApp:
    """
    Agent framework with @agent.tool() decorator, served via FastAPI composition.

    Usage:
        agent = AgentApp(
            name="my_agent",
            description="Does something useful",
            capabilities=["search", "analysis"]
        )

        @agent.tool(description="Search for items")
        async def search(query: str) -> dict:
            return {"results": [...]}

        app = agent.as_fastapi()  # FastAPI app with /invocations, A2A, MCP, health
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
        version: str = "1.0.0",
    ):
        self.agent_metadata = AgentMetadata(
            name=name,
            description=description,
            capabilities=capabilities,
            version=version,
        )

        self.uc_catalog = uc_catalog or os.getenv("UC_CATALOG", "main")
        self.uc_schema = uc_schema or os.getenv("UC_SCHEMA", "agents")
        self.auto_register = auto_register
        self.enable_mcp = enable_mcp
        self._fastapi_app: Optional[FastAPI] = None

    def tool(
        self,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator to register a function as an agent tool.

        Usage:
            @agent.tool(description="Search the database")
            async def search(query: str) -> dict:
                return {...}
        """

        def decorator(func: Callable):
            # Auto-apply @mlflow.trace if mlflow is available
            try:
                import mlflow
                if not getattr(func, "_mlflow_traced", False):
                    func = mlflow.trace(func)
                    func._mlflow_traced = True
            except ImportError:
                pass

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

            return func

        return decorator

    def as_fastapi(self, **kwargs) -> FastAPI:
        """
        Build a FastAPI app with all agent endpoints.

        Returns a fully-wired FastAPI app with:
        - /invocations  (Databricks Responses Agent protocol)
        - /.well-known/agent.json  (A2A agent card)
        - /health  (health check)
        - /api/mcp  (MCP JSON-RPC server, if enabled)
        - /api/tools/<name>  (individual tool endpoints)
        """
        agent_self = self

        @asynccontextmanager
        async def _lifespan(app):
            if agent_self.auto_register:
                await agent_self._register_in_uc()
            yield

        fastapi_app = FastAPI(lifespan=_lifespan, **kwargs)

        self._setup_agent_endpoints(fastapi_app)
        self._setup_invocations(fastapi_app)
        self._setup_tool_endpoints(fastapi_app)

        if self.enable_mcp:
            self._setup_mcp_server(fastapi_app)

        self._fastapi_app = fastapi_app
        return fastapi_app

    # ------------------------------------------------------------------
    # Endpoint setup (called from as_fastapi)
    # ------------------------------------------------------------------

    def _setup_agent_endpoints(self, app: FastAPI):
        """Set up A2A protocol and health endpoints."""
        metadata = self.agent_metadata

        @app.get("/.well-known/agent.json")
        async def agent_card():
            return {
                "schema_version": metadata.protocol_version,
                "name": metadata.name,
                "description": metadata.description,
                "capabilities": metadata.capabilities,
                "version": metadata.version,
                "endpoints": {
                    "invocations": "/invocations",
                    "mcp": "/api/mcp",
                },
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                    for t in metadata.tools
                ],
            }

        @app.get("/.well-known/openid-configuration")
        async def openid_config():
            databricks_host = os.getenv("DATABRICKS_HOST", "")
            if databricks_host and not databricks_host.startswith("http"):
                databricks_host = f"https://{databricks_host}"
            return {
                "issuer": f"{databricks_host}/oidc",
                "authorization_endpoint": f"{databricks_host}/oidc/oauth2/v2.0/authorize",
                "token_endpoint": f"{databricks_host}/oidc/v1/token",
                "jwks_uri": f"{databricks_host}/oidc/v1/keys",
            }

        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "agent": metadata.name,
                "version": metadata.version,
            }

    def _setup_invocations(self, app: FastAPI):
        """
        Set up /invocations endpoint (Databricks Responses Agent protocol).

        Accepts: {"input": [{"role": "user", "content": "..."}]}
        Returns: {"output": [{"type": "message", "content": [{"type": "output_text", "text": "..."}]}]}

        For simple tool agents, extracts the user message and calls the first
        registered tool directly. The /invocations protocol makes sub-agents
        callable the same way Model Serving calls ResponsesAgents.
        """
        agent_self = self

        @app.post("/invocations")
        async def invocations(request: Request):
            body = await request.json()
            input_items = body.get("input", [])

            # Extract the last user message as the query
            query = ""
            for item in reversed(input_items):
                if isinstance(item, dict) and item.get("role") == "user":
                    query = item.get("content", "")
                    break

            if not query:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No user message found in input"},
                )

            # Call the first registered tool with the query
            if not agent_self.agent_metadata.tools:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No tools registered on this agent"},
                )

            tool_def = agent_self.agent_metadata.tools[0]
            try:
                # Determine which parameters the tool accepts
                sig = inspect.signature(tool_def.function)
                params = list(sig.parameters.keys())

                if len(params) == 1:
                    result = await tool_def.function(query)
                else:
                    result = await tool_def.function(query=query)
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_def.name, e, exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={"error": f"Tool execution failed: {str(e)}"},
                )

            # Format result as Responses Agent protocol
            if isinstance(result, dict):
                response_text = result.get("response", json.dumps(result))
            else:
                response_text = str(result)

            return {
                "output": [
                    {
                        "type": "message",
                        "id": f"{agent_self.agent_metadata.name}-response",
                        "content": [
                            {"type": "output_text", "text": response_text}
                        ],
                    }
                ],
                # Pass through structured metadata for observability
                "_metadata": result if isinstance(result, dict) else None,
            }

    def _setup_tool_endpoints(self, app: FastAPI):
        """Register individual tool endpoints at /api/tools/<name>."""
        for tool_def in self.agent_metadata.tools:
            app.post(f"/api/tools/{tool_def.name}")(tool_def.function)

    def _setup_mcp_server(self, app: FastAPI):
        """Set up MCP server endpoints on the FastAPI app."""
        try:
            from ..mcp import MCPServerConfig, setup_mcp_server

            config = MCPServerConfig(
                name=self.agent_metadata.name,
                description=self.agent_metadata.description,
                version=self.agent_metadata.version,
            )

            setup_mcp_server(self, config, fastapi_app=app)
            logger.info("MCP server enabled at /api/mcp")

        except Exception as e:
            logger.warning("MCP server setup failed: %s", e)

    async def _register_in_uc(self):
        """Register agent in Unity Catalog on app startup."""
        try:
            from ..registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError

            app_url = os.getenv("DATABRICKS_APP_URL")
            if not app_url:
                logger.debug("DATABRICKS_APP_URL not set -- skipping UC registration")
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

        except Exception as e:
            logger.warning("UC registration error: %s", e)
