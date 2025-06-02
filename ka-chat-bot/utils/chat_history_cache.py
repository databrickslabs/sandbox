from typing import Dict, List
from collections import defaultdict
import threading
from datetime import datetime
from models import MessageResponse, ChatHistoryItem
from chat_database import ChatDatabase
class ChatHistoryCache:
    """In-memory cache for chat history"""
    def __init__(self, chat_db: ChatDatabase):
        self.cache: Dict[str, ChatHistoryItem] = {}
        self.lock = threading.Lock()
        self.chat_db = chat_db

    def get_history(self, session_id: str) -> ChatHistoryItem:
        """Get chat history from cache"""
        with self.lock:
            return self.cache.get(session_id, None)

    def add_message(self, session_id: str, message: MessageResponse):
        """Add a message to the cache"""
        with self.lock:
            # Add created_at if not present
            if not message.created_at:
                message.created_at = datetime.now().isoformat()
            if not message.timestamp:
                message.timestamp = message.created_at
            if session_id not in self.cache:
                self.cache[session_id] = ChatHistoryItem(sessionId=session_id,
                                                        firstQuery=message.content,
                                                        messages=[],
                                                        timestamp=datetime.now().isoformat(),
                                                        created_at=datetime.now().isoformat())
            
            self.cache[session_id].messages.append(message)
            # Keep only last 10 messages
            if len(self.cache[session_id].messages) > 20:
                self.cache[session_id].messages = self.cache[session_id].messages[-20:]

    def clear_session(self, session_id: str):
        """Clear a session from cache"""
        with self.lock:
            if session_id in self.cache:
                del self.cache[session_id]

    def update_message(self, session_id: str, message_id: str, message: MessageResponse):
        """Update a message in the cache while preserving order"""
        with self.lock:
            if session_id not in self.cache:
                chat_data = self.chat_db.get_chat(session_id, message.user_id)
                if chat_data:
                    self.cache[session_id] = chat_data
                else:
                    raise ValueError("Session id {} not found in cache or DB during update_message.".format(session_id))
            messages = self.cache[session_id].messages
            for msg in messages:
                if msg.message_id == message_id:
                    msg.content = message.content
                    msg.timestamp = message.timestamp
                    break