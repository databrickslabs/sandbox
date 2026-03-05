"""Core agent components: helpers for discoverability, and legacy AgentApp."""

from .helpers import add_agent_card, add_mcp_endpoints
from .agent_app import AgentApp, AgentMetadata, ToolDefinition

__all__ = [
    "add_agent_card",
    "add_mcp_endpoints",
    "AgentApp",
    "AgentMetadata",
    "ToolDefinition",
]
