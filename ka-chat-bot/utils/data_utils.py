from typing import Dict, List, Optional
from datetime import datetime
import copy
import os
import logging
from chat_database import ChatDatabase
from utils.chat_history_cache import ChatHistoryCache
from fastapi import Request, Header, Depends, HTTPException
from datetime import timedelta
from databricks.sdk import WorkspaceClient
from models import MessageResponse

logger = logging.getLogger(__name__)


def get_token(
    x_forwarded_access_token: str = Header(None, alias="X-Forwarded-Access-Token")
) -> str:
    # Try to get the token from the header, else from the environment variable
    if x_forwarded_access_token:
        logger.info(f"get_token: Using X-Forwarded-Access-Token: '{x_forwarded_access_token[:20]}...' (truncated)")
        return x_forwarded_access_token
    else:
        env_token = os.environ.get("LOCAL_API_TOKEN")
        logger.info(f"get_token: No header token, using LOCAL_API_TOKEN: '{env_token[:20] if env_token else 'NOT_SET'}...' (truncated)")
        return env_token

async def check_endpoint_capabilities(
    model: str,
    streaming_support_cache: dict,
    user_access_token: str = Depends(get_token)
) -> tuple[bool, bool]:
    """
    Check if endpoint supports streaming and trace data.
    Returns (supports_streaming, supports_trace)
    """
    client = WorkspaceClient(token=user_access_token, auth_type="pat")
    current_time = datetime.now()
    cache_entry = streaming_support_cache['endpoints'].get(model)
    
    # If cache entry exists and is less than 24 hours old, use cached value
    if cache_entry and (current_time - cache_entry['last_checked']) < timedelta(days=1):
        return cache_entry['supports_streaming'], cache_entry['supports_trace']
    
    # Cache expired or doesn't exist - fetch fresh data
    try:
        endpoint = client.serving_endpoints.get(model)
        supports_trace = any(
            entity.name == 'feedback'
            for entity in endpoint.config.served_entities
        )
        
        # Update cache with fresh data
        streaming_support_cache['endpoints'][model] = {
            'supports_streaming': True,
            'supports_trace': supports_trace,
            'last_checked': current_time
        }
        return True, supports_trace
        
    except Exception as e:
        # If error occurs, return default values
        return True, False


    
async def get_user_info(user_access_token: str = Depends(get_token)) -> dict:
    """Get user information from request headers"""
    try:
        w = WorkspaceClient(token=user_access_token, auth_type="pat")

        current_user = w.current_user.me()
        return {
            "email": current_user.user_name,
            "user_id": current_user.id,
            "username": current_user.user_name,
            "displayName": current_user.display_name
        }
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def load_chat_history(session_id: str, user_id: str, is_first_message: bool, chat_history_cache: ChatHistoryCache, chat_db: ChatDatabase) -> List[Dict]:
    """
    Load chat history with caching mechanism.
    Returns chat history in cache format.
    """
    # Try to get from cache first
    chat_history = copy.deepcopy(chat_history_cache.get_history(session_id))
    if chat_history:
        chat_history = convert_messages_to_cache_format(chat_history.messages)
    # If cache is empty and not first message, load from database
    elif not chat_history and not is_first_message:
        chat_data = chat_db.get_chat(session_id, user_id)
        if chat_data and chat_data.messages:
            # Convert to cache format
            chat_history = convert_messages_to_cache_format(chat_data.messages)
            # Store in cache
            for msg in chat_history:
                message_response = MessageResponse(
                    message_id=msg["message_id"],
                    content=msg["content"],
                    role=msg["role"],
                    timestamp=msg["timestamp"],
                    created_at=msg["created_at"]
                )
                chat_history_cache.add_message(session_id, message_response)
    
    return chat_history or []

def convert_messages_to_cache_format(messages: List) -> List[Dict]:
    """
    Convert database messages to cache format.
    Returns last 20 messages in cache format.
    """
    if not messages:
        return []
    formatted_messages = []
    for msg in messages[-20:]:
        formatted_messages.append({
            "role": msg.role,
            "content": msg.content,
            "message_id": msg.message_id,
            "timestamp": msg.timestamp.isoformat() if isinstance(msg.timestamp, datetime) else msg.timestamp,   
            "created_at": msg.created_at.isoformat() if isinstance(msg.created_at, datetime) else msg.created_at
        })
    return formatted_messages
    
def create_response_data(
    message_id: str,
    content: str,
    sources: Optional[List],
    ttft: Optional[float],
    total_time: float,
    timestamp: Optional[str] = None
) -> Dict:
    """Create standardized response data for both streaming and non-streaming responses."""
    # Convert content to string if it's a dictionary
    if isinstance(content, dict):
        content = content.get('content', '')
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    # Create response data
    response_data = {
        'message_id': message_id,
        'content': content,
        'sources': sources if sources else None,
        'metrics': {
            'timeToFirstToken': ttft,
            'totalTime': total_time
        }
    }
    
    # Add timestamp if provided
    if timestamp:
        response_data['timestamp'] = timestamp
        
    # Convert any datetime objects in the response to strings
    return response_data
