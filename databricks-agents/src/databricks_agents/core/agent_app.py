"""
Core AgentApp class that wraps FastAPI to create discoverable agents.

This is the main entry point for building agent-enabled Databricks Apps.
"""

import os
from typing import Any, Callable, Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Definition of an agent tool (function callable via MCP)."""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class AgentMetadata(BaseModel):
    """Agent metadata for A2A protocol."""
    
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
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.agent_metadata = AgentMetadata(
            name=name,
            description=description,
            capabilities=capabilities
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

        # Register startup event for UC registration
        if self.auto_register:
            self._setup_uc_registration()
        
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
                    "invoke": "/api/invoke"
                },
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                    for tool in self.agent_metadata.tools
                ]
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
                "jwks_uri": f"{databricks_host}/oidc/v1/keys"
            }
        
        @self.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "agent": self.agent_metadata.name,
                "version": self.agent_metadata.version
            }
    
    def tool(
        self,
        description: str,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Decorator to register a function as an agent tool.
        
        Usage:
            @app.tool(description="Search the database")
            async def search(query: str) -> dict:
                return {...}
        """
        def decorator(func: Callable):
            # Extract parameter schema from function signature
            import inspect
            sig = inspect.signature(func)
            
            if parameters is None:
                param_schema = {}
                for name, param in sig.parameters.items():
                    param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
                    param_schema[name] = {
                        "type": param_type.__name__ if hasattr(param_type, '__name__') else "string",
                        "required": param.default == inspect.Parameter.empty
                    }
            else:
                param_schema = parameters
            
            # Register tool
            tool_def = ToolDefinition(
                name=func.__name__,
                description=description,
                parameters=param_schema,
                function=func
            )
            self.agent_metadata.tools.append(tool_def)
            
            # Register as FastAPI endpoint
            self.post(f"/api/tools/{func.__name__}")(func)
            
            return func

        return decorator

    def _setup_uc_registration(self):
        """Set up Unity Catalog registration on startup."""

        @self.on_event("startup")
        async def register_in_uc():
            """Register agent in Unity Catalog on app startup."""
            try:
                from ..registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError

                # Get app URL from environment (set by Databricks Apps runtime)
                app_url = os.getenv("DATABRICKS_APP_URL")
                if not app_url:
                    # Not running in Databricks Apps - skip UC registration
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
                    }
                )

                result = registry.register_agent(spec)
                print(f"✓ Registered agent in UC: {result['full_name']}")

            except UCRegistrationError as e:
                print(f"⚠ UC registration failed: {e}")
            except Exception as e:
                print(f"⚠ UC registration error: {e}")

    def _setup_mcp_server(self):
        """Set up MCP server endpoints."""
        try:
            from ..mcp import setup_mcp_server, MCPServerConfig

            config = MCPServerConfig(
                name=self.agent_metadata.name,
                description=self.agent_metadata.description,
                version=self.agent_metadata.version,
            )

            setup_mcp_server(self, config)
            print(f"✓ MCP server enabled at /api/mcp")

        except Exception as e:
            print(f"⚠ MCP server setup failed: {e}")
