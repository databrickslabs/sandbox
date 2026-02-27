"""
Model Context Protocol (MCP) support.

This module provides utilities for integrating agents with MCP servers
and exposing UC Functions as MCP tools.
"""

from .mcp_server import MCPServer, MCPServerConfig
from .uc_functions import UCFunctionAdapter

__all__ = ["MCPServer", "MCPServerConfig", "UCFunctionAdapter"]
