import json
import time
import asyncio
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
        thinking_content = ""
        response_content = ""
        inside_think_tags = False
        last_chunk_time = time.time()
        heartbeat_interval = 10.0  # Send heartbeat every 45 seconds
        
        try:
            lines_iterator = response.aiter_lines()
            logger.info(f"Started streaming handler with heartbeat interval: {heartbeat_interval}s")
            
            iteration_count = 0
            while True:
                iteration_count += 1
                current_time = time.time()
                time_since_last_chunk = current_time - last_chunk_time
                
                logger.info(f"Iteration {iteration_count}: Time since last chunk: {time_since_last_chunk:.2f}s")
                
                try:
                    # Wait for next line with timeout
                    logger.info(f"Waiting for next line with {heartbeat_interval}s timeout...")
                    line = await asyncio.wait_for(lines_iterator.__anext__(), timeout=heartbeat_interval)
                    logger.info(f"Received raw line: {line}")
                    last_chunk_time = time.time()
                    
                except asyncio.TimeoutError:
                    # No data received within heartbeat interval - send heartbeat
                    current_time = time.time()
                    time_waited = current_time - last_chunk_time
                    logger.info(f"TIMEOUT after {time_waited:.2f}s - Sending heartbeat to prevent proxy timeout")
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "timestamp": current_time,
                        "message": "keeping connection alive"
                    }
                    heartbeat_json = json.dumps(heartbeat_msg)
                    logger.info(f"Yielding heartbeat: {heartbeat_json}")
                    yield f"data: {heartbeat_json}\n\n"
                    last_chunk_time = current_time
                    logger.info("Heartbeat sent, continuing to wait for data...")
                    continue
                
                except StopAsyncIteration:
                    # Stream ended normally
                    logger.info("Stream ended normally (StopAsyncIteration)")
                    break
                
                except Exception as e:
                    logger.error(f"Unexpected error in streaming loop: {type(e).__name__}: {str(e)}")
                    raise
                
                if line.startswith('data: '):
                    json_str = line[6:]
                    
                    # Handle [DONE] marker
                    if json_str.strip() == '[DONE]':
                        logger.info("Received [DONE] marker, ending stream")
                        break
                    
                    try:
                        logger.info(f"Parsing JSON: {json_str[:200]}...")
                        data = json.loads(json_str)
                        logger.info(f"Parsed data: {data}")
                        
                        # Record time of first token
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - start_time
                        
                        # Handle the new format: response.output_text.delta
                        if data.get("type") == "response.output_text.delta":
                            delta_text = data.get("delta", "")
                            logger.info(f"Processing delta: {delta_text[:100]}...")
                            
                            # Track thinking vs response content for final accumulation
                            i = 0
                            while i < len(delta_text):
                                if not inside_think_tags and delta_text[i:i+7] == "<think>":
                                    inside_think_tags = True
                                    thinking_content += "<think>"
                                    i += 7
                                elif inside_think_tags and delta_text[i:i+8] == "</think>":
                                    inside_think_tags = False
                                    thinking_content += "</think>"
                                    i += 8
                                elif inside_think_tags:
                                    thinking_content += delta_text[i]
                                    i += 1
                                else:
                                    response_content += delta_text[i]
                                    i += 1
                            
                            # Add all delta content to accumulated_content (for final storage)
                            accumulated_content += delta_text
                            
                            # Stream all delta content to frontend (including thinking)
                            if delta_text:
                                response_data = create_response_data(
                                    message_id,
                                    delta_text,
                                    sources,
                                    ttft if first_token_time is not None else None,
                                    time.time() - start_time,
                                    original_timestamp
                                )
                                logger.info(f"Yielding real content chunk: {delta_text[:50]}...")
                                yield f"data: {json.dumps(response_data)}\n\n"
                                last_chunk_time = time.time()  # Update heartbeat timer
                                logger.info(f"Updated last_chunk_time to {last_chunk_time}")
                        
                        # Handle the final message with complete content
                        elif data.get("type") == "response.output_item.done":
                            logger.info("Received output_item.done, processing final response")
                            item = data.get("item", {})
                            content_list = item.get("content", [])
                            
                            if content_list and len(content_list) > 0:
                                full_text = content_list[0].get("text", "")
                                logger.info(f"Full text length: {len(full_text)}")
                                
                                # Extract sources from the final response if available
                                # You might need to adjust this based on your source extraction logic
                                if 'databricks_output' in data:
                                    sources = await request_handler.extract_sources_from_trace(data)
                                    
                                # Process the final response to separate thinking from response
                                final_thinking = ""
                                final_response = ""
                                inside_think = False
                                
                                i = 0
                                while i < len(full_text):
                                    if not inside_think and full_text[i:i+7] == "<think>":
                                        inside_think = True
                                        final_thinking += "<think>"
                                        i += 7
                                    elif inside_think and full_text[i:i+8] == "</think>":
                                        inside_think = False
                                        final_thinking += "</think>"
                                        i += 8
                                    elif inside_think:
                                        final_thinking += full_text[i]
                                        i += 1
                                    else:
                                        final_response += full_text[i]
                                        i += 1
                                
                                # Use the final response content
                                accumulated_content = final_response
                                logger.info(f"Final response content length: {len(final_response)}")
                                logger.info(f"Thinking content length: {len(final_thinking)}")
                    
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON: {json_str[:100]}... Error: {e}")
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
            last_heartbeat = start_time
            heartbeat_interval = 45.0
            
            # Send initial heartbeat to keep connection alive during request
            yield f"data: {json.dumps({'type': 'heartbeat', 'message': 'processing request'})}\n\n"
            
            # Start the actual request
            response_task = asyncio.create_task(
                request_handler.enqueue_request(url, headers, request_data)
            )
            
            # Send heartbeats while waiting for response
            while not response_task.done():
                current_time = time.time()
                if current_time - last_heartbeat > heartbeat_interval:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'message': 'still processing'})}\n\n"
                    last_heartbeat = current_time
                
                # Wait a bit before checking again
                await asyncio.sleep(5)
            
            # Get the response once the task is done
            response = await response_task
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