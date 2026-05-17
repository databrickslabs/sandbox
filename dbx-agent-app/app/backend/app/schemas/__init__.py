"""
Pydantic schemas for request/response validation.

This package contains all API schemas:
- app: App creation, update, and response schemas
- mcp_server: MCP server schemas
- tool: Tool schemas and filtering
- collection: Collection and collection item schemas
- discovery: Discovery request and response schemas
- common: Shared schemas and base models
"""

from app.schemas.app import AppCreate, AppUpdate, AppResponse
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate, MCPServerResponse
from app.schemas.tool import ToolResponse, ToolFilter
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionItemCreate,
    CollectionItemResponse,
)
from app.schemas.discovery import (
    DiscoveryRefreshRequest,
    DiscoveryRefreshResponse,
    DiscoveryStatusResponse,
)
from app.schemas.supervisor import (
    SupervisorGenerateRequest,
    SupervisorGenerateResponse,
    SupervisorPreviewResponse,
    SupervisorMetadata,
    SupervisorListResponse,
)
from app.schemas.common import PaginatedResponse, HealthResponse

__all__ = [
    "AppCreate",
    "AppUpdate",
    "AppResponse",
    "MCPServerCreate",
    "MCPServerUpdate",
    "MCPServerResponse",
    "ToolResponse",
    "ToolFilter",
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionItemCreate",
    "CollectionItemResponse",
    "DiscoveryRefreshRequest",
    "DiscoveryRefreshResponse",
    "DiscoveryStatusResponse",
    "SupervisorGenerateRequest",
    "SupervisorGenerateResponse",
    "SupervisorPreviewResponse",
    "SupervisorMetadata",
    "SupervisorListResponse",
    "PaginatedResponse",
    "HealthResponse",
]
