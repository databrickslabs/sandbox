from typing import Optional
from fastapi import FastAPI
from chat_database import ChatDatabase
from .chat_history_cache import ChatHistoryCache
from .message_handler import MessageHandler
from .streaming_handler import StreamingHandler
from .request_handler import RequestHandler
from .config import SERVING_ENDPOINT_NAME
import asyncio
from datetime import datetime

class AppState:
    def __init__(self):
        self.chat_db: Optional[ChatDatabase] = None
        self.chat_history_cache: Optional[ChatHistoryCache] = None
        self.message_handler: Optional[MessageHandler] = None
        self.streaming_handler: Optional[StreamingHandler] = None
        self.request_handler: Optional[RequestHandler] = None
        self.streaming_semaphore: Optional[asyncio.Semaphore] = None
        self.request_queue: Optional[asyncio.Queue] = None
        self.streaming_support_cache = {
            'last_updated': datetime.now(),
            'endpoints': {}  
        }

    def initialize(self):
        """Initialize all dependencies"""
        self.chat_db = ChatDatabase()
        self.chat_history_cache = ChatHistoryCache(self.chat_db)
        self.message_handler = MessageHandler(self.chat_db, self.chat_history_cache)
        self.streaming_handler = StreamingHandler()
        self.request_handler = RequestHandler(SERVING_ENDPOINT_NAME)
        self.streaming_semaphore = self.request_handler.streaming_semaphore
        self.request_queue = self.request_handler.request_queue
        
    async def startup(self, app: FastAPI):
        """Startup tasks"""
        self.initialize()
        asyncio.create_task(self.request_handler.request_worker())

    async def shutdown(self, app: FastAPI):
        """Shutdown tasks"""
        pass

# Create a global app state instance
app_state = AppState() 