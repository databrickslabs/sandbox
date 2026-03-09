"""
SQLAlchemy models for the Multi-Agent Registry.

This package contains all database models:
- App: Databricks Apps metadata
- MCPServer: MCP server configurations
- Tool: Individual tools/functions from MCP servers
- Collection: Curated collections of tools
- CollectionItem: Many-to-many join table for collection membership
"""

from app.models.app import App
from app.models.mcp_server import MCPServer, MCPServerKind
from app.models.tool import Tool
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.supervisor import Supervisor
from app.models.agent import Agent
from app.models.a2a_task import A2ATask
from app.models.discovery_state import DiscoveryState
from app.models.catalog_asset import CatalogAsset
from app.models.workspace_asset import WorkspaceAsset
from app.models.asset_embedding import AssetEmbedding
from app.models.asset_relationship import AssetRelationship
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, ConversationMessage
from app.models.agent_analytics import AgentAnalytics

__all__ = [
    "App",
    "MCPServer",
    "MCPServerKind",
    "Tool",
    "Collection",
    "CollectionItem",
    "Supervisor",
    "Agent",
    "A2ATask",
    "DiscoveryState",
    "CatalogAsset",
    "WorkspaceAsset",
    "AssetEmbedding",
    "AssetRelationship",
    "AuditLog",
    "Conversation",
    "ConversationMessage",
    "AgentAnalytics",
]
