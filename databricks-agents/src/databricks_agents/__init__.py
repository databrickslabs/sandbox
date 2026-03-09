"""
databricks-agent-deploy: Agent platform for Databricks Apps.

Build agents with any framework. Deploy the platform to discover, test, trace, and govern them.

Primary API:
- @app_agent: Decorator to turn an async function into a discoverable agent
- add_agent_card: Make any FastAPI app discoverable via /.well-known/agent.json
- add_mcp_endpoints: Add MCP JSON-RPC endpoints to any FastAPI app

Platform components:
- AgentDiscovery: Discover agents in your Databricks workspace
- DeployEngine: Multi-agent deploy orchestration (agents.yaml -> deploy -> wire -> uc_securable)
- create_dashboard_app: Agent platform dashboard (discovery, testing, lineage, governance)
"""

from .core import (
    add_agent_card,
    add_mcp_endpoints,
    app_agent,
    AppAgent,
    AgentRequest,
    AgentResponse,
    InputItem,
    OutputItem,
    OutputTextContent,
    StreamEvent,
    UserContext,
)
from .discovery import AgentDiscovery, DiscoveredAgent, AgentDiscoveryResult, A2AClient, A2AClientError
from .mcp import MCPServerConfig, setup_mcp_server, UCFunctionAdapter
from .dashboard import create_dashboard_app
from .deploy import DeployConfig, DeployEngine

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("databricks-agent-deploy")
except Exception:
    __version__ = "0.3.0"

__all__ = [
    # Primary API: @app_agent decorator
    "app_agent",
    "AppAgent",
    # Wire protocol types
    "AgentRequest",
    "AgentResponse",
    "InputItem",
    "OutputItem",
    "OutputTextContent",
    "StreamEvent",
    "UserContext",
    # Helpers
    "add_agent_card",
    "add_mcp_endpoints",
    # Discovery
    "AgentDiscovery",
    "DiscoveredAgent",
    "AgentDiscoveryResult",
    "A2AClient",
    "A2AClientError",
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
