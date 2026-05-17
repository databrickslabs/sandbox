"""
API route modules.

This package contains all API route handlers:
- health: Health and readiness checks
- apps: App CRUD operations
- mcp_servers: MCP Server CRUD operations
- tools: Tool listing (read-only)
- collections: Collection and CollectionItem CRUD operations
- discovery: MCP catalog discovery (Phase 2.2)
- supervisors: Supervisor generation (Phase 3.3)
- admin: Admin operations (database management)
- agents: Agent CRUD operations
- chat: Chat interface for testing agents and tools
"""

from . import health, apps, mcp_servers, tools, collections, discovery, supervisors, agents, admin, chat, traces, a2a, catalog_assets, workspace_assets, search, lineage, audit_log, conversations

__all__ = [
    "health",
    "apps",
    "mcp_servers",
    "tools",
    "collections",
    "discovery",
    "supervisors",
    "agents",
    "admin",
    "chat",
    "traces",
    "a2a",
    "catalog_assets",
    "workspace_assets",
    "search",
    "lineage",
    "audit_log",
    "conversations",
]
