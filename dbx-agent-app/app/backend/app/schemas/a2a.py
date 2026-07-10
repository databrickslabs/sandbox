"""
A2A Protocol Pydantic schemas — JSON-RPC request/response, task states, messages, artifacts.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    INPUT_REQUIRED = "input-required"
    AUTH_REQUIRED = "auth-required"
    REJECTED = "rejected"


TERMINAL_STATES = {
    TaskState.COMPLETED,
    TaskState.FAILED,
    TaskState.CANCELED,
    TaskState.REJECTED,
}


class MessagePart(BaseModel):
    text: Optional[str] = None
    mediaType: Optional[str] = None


class A2AMessage(BaseModel):
    messageId: str
    role: str  # "user" or "agent"
    parts: List[MessagePart]
    contextId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class A2AArtifact(BaseModel):
    artifactId: str
    name: Optional[str] = None
    parts: List[MessagePart]


class A2ATaskStatus(BaseModel):
    state: TaskState
    stateReason: Optional[str] = None


class A2ATaskResponse(BaseModel):
    id: str
    contextId: Optional[str] = None
    status: A2ATaskStatus
    messages: List[A2AMessage] = Field(default_factory=list)
    artifacts: List[A2AArtifact] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    method: str
    params: Optional[Dict[str, Any]] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
