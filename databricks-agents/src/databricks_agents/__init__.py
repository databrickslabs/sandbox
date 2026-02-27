"""
databricks-agents: Framework for building discoverable AI agents on Databricks Apps.

This package provides:
- AgentApp: FastAPI wrapper for creating agent-enabled applications
- AgentDiscovery: Discover agents in your Databricks workspace
- A2AClient: Communicate with agents using the A2A protocol
"""

from .core import AgentApp, AgentMetadata, ToolDefinition
from .discovery import AgentDiscovery, DiscoveredAgent, AgentDiscoveryResult, A2AClient, A2AClientError

__version__ = "0.1.0"

__all__ = [
    "AgentApp",
    "AgentMetadata",
    "ToolDefinition",
    "AgentDiscovery",
    "DiscoveredAgent",
    "AgentDiscoveryResult",
    "A2AClient",
    "A2AClientError",
]
