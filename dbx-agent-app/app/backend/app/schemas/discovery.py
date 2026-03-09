"""
Pydantic schemas for Discovery entities.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional


class DiscoveryRefreshRequest(BaseModel):
    """Request schema for discovery refresh endpoint."""

    server_urls: List[HttpUrl] = Field(
        default_factory=list,
        description="List of custom MCP server URLs to discover",
        example=["https://mcp.example.com/api", "https://another-mcp.example.com"],
    )
    discover_workspace: bool = Field(
        default=False,
        description="Discover MCP servers deployed in workspace (stub)",
        example=False,
    )
    discover_catalog: bool = Field(
        default=False,
        description="Discover managed servers from MCP catalog (stub)",
        example=False,
    )
    discover_agents: bool = Field(
        default=False,
        description="Auto-discover agents from serving endpoints and workspace apps",
        example=False,
    )
    databricks_profile: Optional[str] = Field(
        None,
        description="Databricks CLI profile to use for workspace discovery",
        example="fe-vm-serverless-dxukih",
    )


class DiscoveryRefreshResponse(BaseModel):
    """Response from discovery refresh endpoint."""

    status: str = Field(
        ...,
        description="Discovery status (success/partial/failed)",
        example="success",
    )
    message: str = Field(
        ...,
        description="Human-readable message",
        example="Discovery completed successfully",
    )
    apps_discovered: int = Field(
        default=0,
        description="Number of apps discovered",
        example=0,
    )
    servers_discovered: int = Field(
        default=0,
        description="Number of MCP servers discovered",
        example=2,
    )
    tools_discovered: int = Field(
        default=0,
        description="Number of tools discovered",
        example=15,
    )
    new_servers: int = Field(
        default=0,
        description="Number of new servers added",
        example=1,
    )
    updated_servers: int = Field(
        default=0,
        description="Number of existing servers updated",
        example=1,
    )
    new_tools: int = Field(
        default=0,
        description="Number of new tools added",
        example=10,
    )
    updated_tools: int = Field(
        default=0,
        description="Number of existing tools updated",
        example=5,
    )
    agents_discovered: int = Field(
        default=0,
        description="Number of agents discovered from serving endpoints and apps",
        example=0,
    )
    new_agents: int = Field(
        default=0,
        description="Number of new agents added",
        example=0,
    )
    updated_agents: int = Field(
        default=0,
        description="Number of existing agents updated",
        example=0,
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered during discovery",
        example=[],
    )


class WorkspaceProfileResponse(BaseModel):
    """A single Databricks workspace profile with auth status."""

    name: str = Field(..., description="Profile name from ~/.databrickscfg")
    host: Optional[str] = Field(None, description="Workspace URL")
    auth_type: Optional[str] = Field(None, description="Authentication type (pat, oauth-m2m, etc.)")
    is_account_profile: bool = Field(False, description="Whether this is an account-level profile")
    auth_valid: bool = Field(False, description="Whether authentication succeeded")
    auth_error: Optional[str] = Field(None, description="Error message if auth failed")
    username: Optional[str] = Field(None, description="Authenticated username")


class WorkspaceProfilesResponse(BaseModel):
    """Response from workspace profiles discovery endpoint."""

    profiles: List[WorkspaceProfileResponse] = Field(
        default_factory=list, description="List of discovered workspace profiles"
    )
    config_path: str = Field(..., description="Path to the databrickscfg file used")
    total: int = Field(0, description="Total number of profiles found")
    valid: int = Field(0, description="Number of profiles with valid auth")


class DiscoveryStatusResponse(BaseModel):
    """Response from discovery status endpoint."""

    is_running: bool = Field(
        ...,
        description="Whether discovery is currently running",
        example=False,
    )
    last_run_timestamp: Optional[str] = Field(
        None,
        description="ISO timestamp of last discovery run",
        example="2026-02-10T10:30:00Z",
    )
    last_run_status: Optional[str] = Field(
        None,
        description="Status of last run (success/partial/failed)",
        example="success",
    )
    last_run_message: Optional[str] = Field(
        None,
        description="Message from last run",
        example="Discovery completed successfully",
    )
