"""
Pydantic schemas for Supervisor generation endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime


class SupervisorGenerateRequest(BaseModel):
    """Schema for generating a supervisor from a collection."""

    collection_id: int = Field(
        ...,
        description="Collection ID to generate supervisor from",
        example=1,
    )
    llm_endpoint: str = Field(
        default="databricks-meta-llama-3-1-70b-instruct",
        description="Databricks Foundation Model endpoint name",
        example="databricks-meta-llama-3-1-70b-instruct",
    )
    app_name: Optional[str] = Field(
        None,
        description="Custom app name (defaults to normalized collection name)",
        example="expert-research-toolkit",
    )
    mode: Optional[str] = Field(
        default="code-first",
        description="Generation mode (accepted but used for frontend compatibility)",
        example="code-first",
    )


class SupervisorGenerateResponse(BaseModel):
    """Schema for supervisor generation response."""

    collection_id: int = Field(
        ...,
        description="Collection ID used for generation",
        example=1,
    )
    collection_name: str = Field(
        ...,
        description="Collection name",
        example="Expert Research Toolkit",
    )
    app_name: str = Field(
        ...,
        description="Generated app name",
        example="expert-research-toolkit",
    )
    files: Dict[str, str] = Field(
        ...,
        description="Generated files (filename -> content)",
        example={
            "supervisor.py": "# Generated supervisor code...",
            "requirements.txt": "fastapi\nuvicorn\n",
            "app.yaml": "name: expert-research-toolkit\n",
        },
    )
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of generation",
        example="2024-01-15T10:30:00Z",
    )
    supervisor_url: Optional[str] = Field(
        None,
        description="Deployed supervisor URL (placeholder in local dev)",
        example="https://example.databricks.com/apps/expert-research-toolkit",
    )
    code: Optional[str] = Field(
        None,
        description="Generated supervisor.py content",
        example="# Generated supervisor code...",
    )


class SupervisorPreviewResponse(BaseModel):
    """Schema for supervisor preview response."""

    collection_id: int = Field(
        ...,
        description="Collection ID",
        example=1,
    )
    collection_name: str = Field(
        ...,
        description="Collection name",
        example="Expert Research Toolkit",
    )
    app_name: str = Field(
        ...,
        description="App name that would be generated",
        example="expert-research-toolkit",
    )
    mcp_server_urls: list[str] = Field(
        ...,
        description="MCP server URLs that will be included",
        example=["https://mcp1.example.com", "https://mcp2.example.com"],
    )
    tool_count: int = Field(
        ...,
        description="Number of tools/items in collection",
        example=5,
    )
    preview: Dict[str, str] = Field(
        ...,
        description="Preview of generated files (filename -> first 500 chars)",
        example={
            "supervisor.py": "# Generated supervisor code...",
            "requirements.txt": "fastapi\nuvicorn\n",
            "app.yaml": "name: expert-research-toolkit\n",
        },
    )


class SupervisorMetadata(BaseModel):
    """Schema for supervisor metadata tracking."""

    id: int = Field(..., description="Supervisor ID", example=1)
    collection_id: int = Field(..., description="Collection ID", example=1)
    app_name: str = Field(..., description="App name", example="expert-research-toolkit")
    generated_at: datetime = Field(
        ...,
        description="Generation timestamp",
        example="2024-01-15T10:30:00",
    )
    deployed_url: Optional[str] = Field(
        None,
        description="Deployed app URL (if deployed)",
        example="https://example.databricks.com/apps/expert-research-toolkit",
    )

    class Config:
        from_attributes = True


class SupervisorListResponse(BaseModel):
    """Schema for listing generated supervisors."""

    supervisors: list[SupervisorMetadata] = Field(
        ...,
        description="List of generated supervisors",
    )
    total: int = Field(..., description="Total count", example=5)
