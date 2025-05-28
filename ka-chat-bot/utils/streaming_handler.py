import json
import time
from typing import AsyncGenerator, Optional, Dict
from fastapi.responses import StreamingResponse
import httpx
from models import MessageResponse
from utils import *
from utils.data_utils import create_response_data
import logging
import uuid
from utils.request_handler import RequestHandler
from datetime import datetime
from utils.config import SERVING_ENDPOINT_NAME
logger = logging.getLogger(__name__)
class StreamingHandler:

    @staticmethod
    async def handle_streaming_response(
        response: httpx.Response,
        request_data: Dict,
        headers: Dict,
        session_id: str,
        message_id: str,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        start_time: float,
        first_token_time: Optional[float],
        accumulated_content: str,
        sources: Optional[Dict],
        ttft: Optional[float],
        request_handler: RequestHandler,
        message_handler,
        streaming_support_cache,
        supports_trace,
        update_flag: bool
    ) -> AsyncGenerator[str, None]:
        """Handle streaming response from the model."""
        try:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    try:
                        json_str = line[6:]
                        data = json.loads(json_str)
                        # Record time of first token
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - start_time
                            
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            accumulated_content += content
                            # Extract sources if this is the final message containing databricks_options
                            if 'databricks_output' in data:
                                sources = await request_handler.extract_sources_from_trace(data)
                            # Include the same message_id in each chunk
                            response_data = create_response_data(
                                message_id,
                                content if content else None,
                                sources,
                                ttft if first_token_time is not None else None,
                                time.time() - start_time,
                                original_timestamp
                            )
                            
                            yield f"data: {json.dumps(response_data)}\n\n"
                        if "delta" in data:
                            delta = data["delta"]
                            if delta["role"] == "assistant" and "tool_calls" in delta:
                                content = "Searching for information..."
                            elif delta["role"] == "tool":
                                content = "Processing response..."
                            elif delta["role"] == "assistant" and delta.get("content"):
                                content = delta['content']
                                accumulated_content += content
                            response_data = create_response_data(
                                message_id,
                                content+"\n\n",
                                sources,
                                ttft if first_token_time is not None else None,
                                time.time() - start_time,
                                original_timestamp
                            )
                            yield f"data: {json.dumps(response_data)}\n\n"    
                    except json.JSONDecodeError:
                        continue
            if update_flag:
                updated_message = message_handler.update_message(
                                    session_id=session_id,
                                    message_id=message_id,
                                    user_id=user_id,
                                    content=accumulated_content,
                                    sources=sources,
                                    timestamp=original_timestamp,
                                    metrics={
                                        "timeToFirstToken": ttft,
                                        "totalTime": time.time() - start_time
                                    }
                                )
            else:
                assistant_message = message_handler.create_message(
                                    message_id=message_id,
                                    content=accumulated_content,
                                    role="assistant",
                                    session_id=session_id,
                                    user_id=user_id,
                                    user_info=user_info,
                                    sources=sources,
                                    metrics={'timeToFirstToken': ttft, 'totalTime': time.time() - start_time}
                                )
                streaming_support_cache['endpoints'][SERVING_ENDPOINT_NAME] = {
                    'supports_streaming': True,
                    'supports_trace': supports_trace,
                    'last_checked': datetime.now()
                }

            final_response = {
                'message_id': message_id,
                'sources': sources,
            }
            yield f"data: {json.dumps(final_response)}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            raise

    @staticmethod
    async def handle_non_streaming_response(
        request_handler,
        url: str,
        headers: Dict,
        request_data: Dict,
        session_id: str,
        user_id: str,
        user_info: Dict,
        message_handler
    ) -> AsyncGenerator[str, None]:
        """Handle non-streaming response from the model."""
        try:
            start_time = time.time()
            response = await request_handler.enqueue_request(url, headers, request_data)
            response_data = await request_handler.handle_databricks_response(response, start_time)
            
            assistant_message = message_handler.create_message(
                message_id=str(uuid.uuid4()),
                content=response_data["content"],
                role="assistant",
                session_id=session_id,
                user_id=user_id,
                user_info=user_info,
                sources=response_data.get("sources"),
                metrics=response_data.get("metrics")
            )
            
            yield f"data: {assistant_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Error in non-streami ng response: {str(e)}")
            error_message = message_handler.create_error_message(
                session_id=session_id,
                user_id=user_id,
                error_content="Request timed out. " + str(e) + " Please try again later."
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"

    @staticmethod
    async def handle_streaming_regeneration(
        response: httpx.Response,
        request_data: Dict,
        headers: Dict,
        session_id: str,
        message_id: str,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        start_time: float,
        first_token_time: Optional[float],
        accumulated_content: str,
        sources: Optional[Dict],
        ttft: Optional[float],
        request_handler: RequestHandler,
        message_handler,
        streaming_support_cache,
        supports_trace,
        update_flag: bool
    ) -> AsyncGenerator[str, None]:
        """Handle streaming message regeneration."""
        try:
            async for response_chunk in StreamingHandler.handle_streaming_response(
                response, request_data, headers, session_id, message_id, user_id,user_info,
                original_timestamp, start_time, first_token_time, accumulated_content,
                sources, ttft, request_handler, message_handler, streaming_support_cache, supports_trace, update_flag    
            ):
                yield response_chunk
        except Exception as e:
            logger.error(f"Error in streaming regeneration: {str(e)}")
            error_message = message_handler.create_error_message(
                session_id=session_id,
                user_id=user_id,
                error_content="Failed to regenerate response. " + str(e)
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n" 

    @staticmethod
    async def handle_non_streaming_regeneration(
        request_handler,
        session_id: str,
        message_id: str,
        url: str,
        headers: Dict,
        request_data: Dict,
        user_id: str,
        user_info: Dict,
        original_timestamp: str,
        first_token_time: Optional[float],
        sources: Optional[Dict],
        ttft: Optional[float],
        message_handler
    ) -> AsyncGenerator[str, None]:
        """Handle non-streaming message regeneration."""    
        try:
            start_time = time.time()
            response = await request_handler.enqueue_request(url, headers, request_data)
            response_data = await request_handler.handle_databricks_response(response, start_time)
            
            update_message = message_handler.update_message(
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                content=response_data["content"],
                sources=response_data.get("sources", []),
                timestamp=original_timestamp,
                metrics=response_data.get("metrics", {}),
            )
            
            yield f"data: {update_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"   
        except Exception as e:
            logger.error(f"Error in non-streaming regeneration: {str(e)}")
            error_message = message_handler.update_message(
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                content="Failed to regenerate response. " + str(e) + " Please try again.",
                sources=[],
                timestamp=original_timestamp,
                metrics=None
            )
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n" 