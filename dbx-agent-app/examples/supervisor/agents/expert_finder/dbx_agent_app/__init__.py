"""
dbx-agent-app: Framework for building discoverable AI agents on Databricks Apps.

This package provides:
- @app_agent: Decorator to turn an async function into a discoverable agent
- AgentDiscovery: Discover agents in your Databricks workspace
- A2AClient: Communicate with agents using the A2A protocol
- UCAgentRegistry: Register agents in Unity Catalog
- MCPServerConfig: Configure MCP server for agent tools
"""

from .discovery import AgentDiscovery, DiscoveredAgent, AgentDiscoveryResult, A2AClient, A2AClientError
from .mcp import MCPServerConfig, setup_mcp_server, UCFunctionAdapter
from .registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError
from .dashboard import create_dashboard_app

try:
    from importlib.metadata import version
    __version__ = version("dbx-agent-app")
except Exception:
    __version__ = "0.1.0"

__all__ = [
    # Discovery
    "AgentDiscovery",
    "DiscoveredAgent",
    "AgentDiscoveryResult",
    "A2AClient",
    "A2AClientError",
    # Registry
    "UCAgentRegistry",
    "UCAgentSpec",
    "UCRegistrationError",
    # MCP
    "MCPServerConfig",
    "setup_mcp_server",
    "UCFunctionAdapter",
    # Dashboard
    "create_dashboard_app",
]

