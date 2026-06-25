"""
Agent discovery for Databricks Apps.

This module provides clients and utilities for discovering agent-enabled
Databricks Apps that expose A2A protocol agent cards.
"""

from .agent_discovery import (
    AgentDiscovery,
    DiscoveredAgent,
    AgentDiscoveryResult,
)
from .a2a_client import (
    A2AClient,
    A2AClientError,
)

__all__ = [
    "AgentDiscovery",
    "DiscoveredAgent",
    "AgentDiscoveryResult",
    "A2AClient",
    "A2AClientError",
]
