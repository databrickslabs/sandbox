"""
Model Context Protocol (MCP) support.

This module provides utilities for integrating agents with MCP servers
and exposing UC Functions as MCP tools.
"""

from .mcp_server import MCPServer, MCPServerConfig, setup_mcp_server
from .uc_functions import UCFunctionAdapter

__all__ = ["MCPServer", "MCPServerConfig", "setup_mcp_server", "UCFunctionAdapter"]
