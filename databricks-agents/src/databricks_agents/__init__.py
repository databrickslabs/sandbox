"""
databricks-agents: Framework for building discoverable AI agents on Databricks Apps.

This package provides:
- AgentApp: FastAPI wrapper for creating agent-enabled applications
- AgentDiscovery: Discover agents in your Databricks workspace
- A2AClient: Communicate with agents using the A2A protocol
- UCAgentRegistry: Register agents in Unity Catalog
- MCPServerConfig: Configure MCP server for agent tools
"""

from .core import AgentApp, AgentMetadata, ToolDefinition
from .discovery import AgentDiscovery, DiscoveredAgent, AgentDiscoveryResult, A2AClient, A2AClientError
from .mcp import MCPServerConfig, setup_mcp_server, UCFunctionAdapter
from .registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError

try:
    from importlib.metadata import version
    __version__ = version("databricks-agents")
except Exception:
    __version__ = "0.1.0"

__all__ = [
    # Core
    "AgentApp",
    "AgentMetadata",
    "ToolDefinition",
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
]
