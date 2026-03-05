"""
databricks-agent-deploy: Agent platform for Databricks Apps.

Build agents with any framework. Deploy the platform to discover, test, trace, and govern them.

Primary API (helpers for agent developers):
- add_agent_card: Make any FastAPI app discoverable via /.well-known/agent.json
- add_mcp_endpoints: Add MCP JSON-RPC endpoints to any FastAPI app

Platform components:
- AgentDiscovery: Discover agents in your Databricks workspace
- UCAgentRegistry: Register agents in Unity Catalog
- DeployEngine: Multi-agent deploy orchestration (agents.yaml -> deploy -> wire -> permissions)
- create_dashboard_app: Agent platform dashboard (discovery, testing, lineage, governance)

Legacy (still works, but prefer helpers + official Databricks SDK):
- AgentApp: Agent framework with @agent.tool() decorator
"""

from .core import add_agent_card, add_mcp_endpoints, AgentApp, AgentMetadata, ToolDefinition
from .discovery import AgentDiscovery, DiscoveredAgent, AgentDiscoveryResult, A2AClient, A2AClientError
from .mcp import MCPServerConfig, setup_mcp_server, UCFunctionAdapter
from .registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError
from .dashboard import create_dashboard_app
from .deploy import DeployConfig, DeployEngine

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("databricks-agent-deploy")
except Exception:
    __version__ = "0.3.0"

__all__ = [
    # Helpers (primary API for agent developers)
    "add_agent_card",
    "add_mcp_endpoints",
    # Legacy
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
    # Dashboard
    "create_dashboard_app",
    # Deploy
    "DeployConfig",
    "DeployEngine",
]
