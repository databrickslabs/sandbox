from fastapi import Depends
from .app_state import app_state

def get_chat_db():
    return app_state.chat_db

def get_chat_history_cache():
    return app_state.chat_history_cache

def get_message_handler():
    return app_state.message_handler

def get_streaming_handler():
    return app_state.streaming_handler

def get_request_handler():
    return app_state.request_handler

def get_streaming_semaphore():
    return app_state.streaming_semaphore

def get_request_queue():
    return app_state.request_queue

def get_streaming_support_cache():
    return app_state.streaming_support_cache 