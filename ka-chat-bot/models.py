from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class MessageRequest(BaseModel):
    content: str
    session_id: str
    include_history: bool = True
    serving_endpoint_name: Optional[str] = None

class MessageResponse(BaseModel):
    message_id: str
    content: str
    role: str
    model: Optional[str] = None
    timestamp: datetime
    created_at: Optional[datetime] = None
    sources: Optional[List[Dict]] = None
    metrics: Optional[Dict] = None
    isThinking: Optional[bool] = None

class ChatHistoryItem(BaseModel):
    sessionId: str  
    firstQuery: str  
    messages: List[MessageResponse]
    timestamp: datetime
    created_at: Optional[datetime] = None
    isActive: bool = True 

class ChatHistoryResponse(BaseModel):
    sessions: List[ChatHistoryItem]

class CreateChatRequest(BaseModel):
    title: str

class RegenerateRequest(BaseModel):
    message_id: str
    original_content: str
    session_id: str 
    include_history: bool = True
    serving_endpoint_name: Optional[str] = None