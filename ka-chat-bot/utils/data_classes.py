from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from .request_handler import RequestHandler
from .message_handler import MessageHandler

@dataclass
class StreamingContext:
    """Context for streaming operations"""
    session_id: str
    user_id: str
    user_info: Dict[str, Any]
    start_time: float
    first_token_time: Optional[float] = None
    accumulated_content: str = ""
    sources: Optional[Dict] = None
    ttft: Optional[float] = None
    original_timestamp: Optional[str] = None

@dataclass
class RequestContext:
    """Context for request handling"""
    url: str
    headers: Dict[str, str]
    request_data: Dict[str, Any]
    streaming_timeout: Optional[float] = None
    supports_streaming: bool = False
    supports_trace: bool = False

@dataclass
class HandlerContext:
    """Context for handler operations"""
    request_handler: RequestHandler
    message_handler: MessageHandler
    streaming_support_cache: Dict[str, Any]
    streaming_semaphore: asyncio.Semaphore
    request_queue: asyncio.Queue

@dataclass
class MessageContext:
    """Context for message operations"""
    message_id: str
    content: str
    role: str
    session_id: str
    user_id: str
    user_info: Optional[Dict[str, Any]] = None
    sources: Optional[list] = None
    metrics: Optional[Dict[str, Any]] = None
    is_first_message: bool = False 