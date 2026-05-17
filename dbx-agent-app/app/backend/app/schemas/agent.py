"""
Pydantic schemas for Agent entities.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class A2ASkill(BaseModel):
    """A2A skill descriptor."""

    id: str = Field(..., description="Skill identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="What the skill does")
    tags: Optional[List[str]] = Field(None, description="Skill tags")


class A2ACapabilities(BaseModel):
    """A2A agent capabilities."""

    streaming: bool = Field(False, description="Supports SSE streaming")
    pushNotifications: bool = Field(False, description="Supports push notifications")


class AgentBase(BaseModel):
    """Base schema for Agent with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Agent name",
        example="Research Agent",
    )
    description: Optional[str] = Field(
        None,
        description="What the agent does",
        example="Searches expert transcripts and profiles",
    )
    capabilities: Optional[str] = Field(
        None,
        description="Comma-separated capability tags",
        example="search,analysis,reporting",
    )
    status: Optional[str] = Field(
        "draft",
        description="Agent status: draft, active, inactive, error",
        example="active",
    )
    collection_id: Optional[int] = Field(
        None,
        description="ID of the linked collection (tool set)",
        example=1,
    )
    endpoint_url: Optional[str] = Field(
        None,
        description="Serving endpoint or runtime URL",
        example="https://my-workspace.cloud.databricks.com/serving-endpoints/agent-1",
    )
    # A2A Protocol fields
    a2a_capabilities: Optional[str] = Field(
        None,
        description='JSON: {"streaming": true, "pushNotifications": false}',
    )
    skills: Optional[str] = Field(
        None,
        description='JSON array of A2A skill descriptors',
    )
    protocol_version: Optional[str] = Field(
        None,
        description="A2A protocol version",
        example="0.3.0",
    )
    system_prompt: Optional[str] = Field(
        None,
        description="Rich persona / instructions for LLM when processing A2A tasks",
    )


class AgentCreate(AgentBase):
    """Schema for creating a new Agent. Status defaults to 'draft'."""

    auth_token: Optional[str] = Field(None, description="Bearer token for inbound A2A auth")


class AgentUpdate(BaseModel):
    """Schema for updating an Agent. All fields are optional."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Agent name",
    )
    description: Optional[str] = Field(None, description="What the agent does")
    capabilities: Optional[str] = Field(None, description="Comma-separated capability tags")
    status: Optional[str] = Field(None, description="Agent status")
    collection_id: Optional[int] = Field(None, description="Linked collection ID")
    endpoint_url: Optional[str] = Field(None, description="Serving endpoint URL")
    auth_token: Optional[str] = Field(None, description="Bearer token for inbound A2A auth")
    a2a_capabilities: Optional[str] = Field(None, description="A2A capabilities JSON")
    skills: Optional[str] = Field(None, description="A2A skills JSON array")
    protocol_version: Optional[str] = Field(None, description="A2A protocol version")
    system_prompt: Optional[str] = Field(None, description="Rich persona / instructions for LLM")


class AgentResponse(AgentBase):
    """Schema for Agent response (excludes auth_token for security)."""

    id: int = Field(..., description="Agent ID", example=1)
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class AgentCardResponse(BaseModel):
    """A2A-compliant Agent Card response."""

    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    protocolVersion: str = "0.3.0"
    url: str
    capabilities: A2ACapabilities = Field(default_factory=A2ACapabilities)
    skills: List[A2ASkill] = Field(default_factory=list)
    securitySchemes: Optional[dict] = None
    security: Optional[list] = None
