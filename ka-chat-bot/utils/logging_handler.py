import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps

# Context variable to store request-specific data
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

    def _format_log(self, 
                   level: str, 
                   message: str, 
                   correlation_id: Optional[str] = None, 
                   **kwargs) -> Dict[str, Any]:
        """Format log message with consistent structure"""
        context = request_context.get()
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'correlation_id': correlation_id or context.get('correlation_id'),
            'session_id': context.get('session_id'),
            'user_id': context.get('user_id'),
            **kwargs
        }
        return log_data

    def info(self, message: str, **kwargs):
        """Log info level message"""
        log_data = self._format_log('INFO', message, **kwargs)
        self.logger.info(json.dumps(log_data))

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error level message"""
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error)
        } if error else {}
        log_data = self._format_log('ERROR', message, **{**error_details, **kwargs})
        self.logger.error(json.dumps(log_data))

    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        log_data = self._format_log('DEBUG', message, **kwargs)
        self.logger.debug(json.dumps(log_data))

def with_logging(func):
    """Decorator to add logging context to functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())
        try:
            # Extract relevant context from kwargs
            context = {
                'correlation_id': correlation_id,
                'session_id': kwargs.get('session_id'),
                'user_id': kwargs.get('user_id'),
                'timestamp': datetime.utcnow().isoformat(),
            }
            token = request_context.set(context)
            
            logger = StructuredLogger(__name__)
            logger.info(f"Starting {func.__name__}", 
                       function=func.__name__,
                       args=str(args))
            
            result = await func(*args, **kwargs)
            
            logger.info(f"Completed {func.__name__}", 
                       function=func.__name__,
                       duration_ms=(datetime.utcnow() - datetime.fromisoformat(context['timestamp'])).total_seconds() * 1000)
            
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}",
                        error=e,
                        function=func.__name__)
            raise
        finally:
            request_context.reset(token)
    
    return wrapper

