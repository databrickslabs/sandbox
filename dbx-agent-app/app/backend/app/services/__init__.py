"""
Services for the Multi-Agent Registry API.

This package contains business logic services for:
- MCP client integration (mcp_client.py)
- Tool specification parsing (tool_parser.py)
- Discovery orchestration (discovery.py)
- Code generation (generator.py)
"""

from app.services.mcp_client import MCPClient, MCPConnectionError, MCPTimeoutError
from app.services.tool_parser import ToolParser, normalize_tool_spec
from app.services.discovery import DiscoveryService
from app.services.generator import GeneratorService, GeneratorError, get_generator_service

__all__ = [
    "MCPClient",
    "MCPConnectionError",
    "MCPTimeoutError",
    "ToolParser",
    "normalize_tool_spec",
    "DiscoveryService",
    "GeneratorService",
    "GeneratorError",
    "get_generator_service",
]
