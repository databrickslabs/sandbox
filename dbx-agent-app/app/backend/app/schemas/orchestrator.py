"""
Pydantic schemas for the multi-agent orchestration endpoint.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class OrchestrationChatRequest(BaseModel):
    """Chat request with optional multi-agent orchestration."""

    collection_id: int = Field(..., description="Collection ID to use for supervisor")
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    orchestration_mode: bool = Field(
        default=False,
        description="Enable multi-agent orchestration (plan, route, execute, evaluate)",
    )
    mock_mode: bool = Field(True, description="Use mock responses (no real LLM/MCP calls)")


class SubTaskResultItem(BaseModel):
    """Result from a single orchestrated sub-task."""

    task_index: int
    agent_id: int
    agent_name: str
    description: str
    response: str
    latency_ms: int
    success: bool
    error: Optional[str] = None


class OrchestrationChatResponse(BaseModel):
    """Chat response from orchestrated supervisor."""

    response: str
    conversation_id: str
    plan: Optional[Dict[str, Any]] = Field(
        None, description="The decomposition plan (complexity, reasoning, sub-tasks)"
    )
    sub_task_results: Optional[List[SubTaskResultItem]] = None
    agents_used: int = 0
    tools_discovered: int = 0
    tools_called: int = 0
    quality_score: Optional[float] = None
    mock: bool = False
