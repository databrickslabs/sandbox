from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Response, Request, Query, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, RedirectResponse
from typing import Dict, List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointStateReady
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime, timedelta
import json
import httpx
import time  
import logging
import asyncio
from chat_database import ChatDatabase
from collections import defaultdict
from contextlib import asynccontextmanager
from models import MessageRequest, MessageResponse, ChatHistoryItem, ChatHistoryResponse, CreateChatRequest, RegenerateRequest
from utils.config import SERVING_ENDPOINT_NAME, DATABRICKS_HOST
from utils import *
from utils.logging_handler import with_logging
from utils.app_state import app_state
from utils.dependencies import (
    get_chat_db,
    get_chat_history_cache,
    get_message_handler,
    get_streaming_handler,
    get_request_handler,
    get_streaming_semaphore,
    get_request_queue,
    get_streaming_support_cache
)
from utils.data_classes import StreamingContext, RequestContext, HandlerContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # This will output to console
    ]
)

logger = logging.getLogger(__name__)
load_dotenv(override=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await app_state.startup(app)
    yield
    await app_state.shutdown(app)

app = FastAPI(lifespan=lifespan)

class CachedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

ui_app = CachedStaticFiles(directory="frontend/build-chat-app", html=True)
api_app = FastAPI()
app.mount("/chat-api", api_app)
app.mount("/", ui_app)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get auth headers
async def get_auth_headers(
    token: str = Depends(get_token)
) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="No access token provided in header or environment variable")
    return {"Authorization": f"Bearer {token}"}
    

# Routes
@api_app.get("/")
async def root():
    return {"message": "Databricks Chat API is running"}

# Modify the chat endpoint to handle sessions
@api_app.post("/chat")
async def chat(
    message: MessageRequest,
    user_info: dict = Depends(get_user_info),
    headers: dict = Depends(get_auth_headers),
    chat_db: ChatDatabase = Depends(get_chat_db),
    chat_history_cache: ChatHistoryCache = Depends(get_chat_history_cache),
    message_handler: MessageHandler = Depends(get_message_handler),
    streaming_handler: StreamingHandler = Depends(get_streaming_handler),
    request_handler: RequestHandler = Depends(get_request_handler),
    streaming_semaphore: asyncio.Semaphore = Depends(get_streaming_semaphore),
    request_queue: asyncio.Queue = Depends(get_request_queue),
    streaming_support_cache: dict = Depends(get_streaming_support_cache)
):
    logger.info(f"Chat endpoint called with session_id: {message.session_id}, content length: {len(message.content) if message.content else 0}")
    try:
        user_id = user_info["user_id"]
        logger.info(f"Processing request for user_id: {user_id}")
        is_first_message = chat_db.is_first_message(message.session_id, user_id)
        logger.info(f"Is first message: {is_first_message}")
        user_message = message_handler.create_message(
            message_id=str(uuid.uuid4()),
            content=message.content,
            role="user",
            session_id=message.session_id,
            user_id=user_id,
            user_info=user_info,
            is_first_message=is_first_message
        )
        # Load chat history with caching
        logger.info(f"Loading chat history for session {message.session_id}")
        chat_history = await load_chat_history(message.session_id, user_id, is_first_message, chat_history_cache, chat_db)
        logger.info(f"Loaded {len(chat_history)} messages from chat history")
        
        async def generate():
            logger.info("Starting response generation")
            
            streaming_timeout = httpx.Timeout(
                connect=8.0,
                read=120.0,
                write=8.0,
                pool=8.0
            )
            # Get the serving endpoint name from the request
            serving_endpoint_name = SERVING_ENDPOINT_NAME
            endpoint_url = f"https://{DATABRICKS_HOST}/serving-endpoints/{serving_endpoint_name}/invocations"
            logger.info(f"Using endpoint: {endpoint_url}")
            
            supports_streaming = await check_endpoint_capabilities(serving_endpoint_name, streaming_support_cache)
            logger.info(f"Endpoint {serving_endpoint_name} supports_streaming: {supports_streaming}")
            request_data = {
                "input": [
                    *([{"role": msg["role"], "content": msg["content"]} for msg in chat_history[:-1]] 
                        if message.include_history else []),
                    {"role": "user", "content": message.content}
                ]
            }
            request_data["databricks_options"] = {"return_trace": True}

            if not supports_streaming:
                logger.info("Using non-streaming mode")
                async for response_chunk in streaming_handler.handle_non_streaming_response(
                    request_handler, endpoint_url, headers, request_data, message.session_id, user_id, user_info, message_handler
                ):
                    yield response_chunk
            else:
                logger.info("Using streaming mode")
                async with streaming_semaphore:
                    logger.info("Acquired streaming semaphore")
                    async with httpx.AsyncClient(timeout=streaming_timeout) as streaming_client:
                        try:
                            request_data["stream"] = True
                            assistant_message_id = str(uuid.uuid4())
                            logger.info(f"Generated assistant message ID: {assistant_message_id}")
                            first_token_time = None
                            accumulated_content = ""
                            ttft = None
                            start_time = time.time()
                            logger.info(f"Starting streaming request at {start_time}")

                            logger.info(f"Making streaming POST request to {endpoint_url}")
                            logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")
                            
                            # Make the streaming request directly without heartbeats
                            async with streaming_client.stream('POST', 
                                endpoint_url,
                                headers=headers,
                                json=request_data,
                                timeout=streaming_timeout
                            ) as response:
                                logger.info(f"Received response with status code: {response.status_code}")
                                if response.status_code == 200:
                                    logger.info("Starting to process streaming response")
                                    logger.info("Calling streaming_handler.handle_streaming_response")
                                    async for response_chunk in streaming_handler.handle_streaming_response(
                                        response, request_data, headers, message.session_id, assistant_message_id,
                                        user_id, user_info, None, start_time, first_token_time,
                                        accumulated_content, None, ttft, request_handler, message_handler,
                                        streaming_support_cache, True, False
                                    ):
                                        logger.info(f"Main: Got response chunk from streaming handler")
                                        yield response_chunk
                                else:
                                    logger.error(f"Streaming request failed with status code: {response.status_code}")
                                    logger.error(f"Response headers: {dict(response.headers)}")
                                    response_text = await response.aread()
                                    logger.error(f"Response body: {response_text.decode('utf-8', errors='ignore')[:1000]}")
                                    raise Exception(f"Streaming not supported - HTTP {response.status_code}")
                        except (httpx.ReadTimeout, httpx.HTTPError, Exception) as e:
                            logger.error(f"Streaming failed with error type: {type(e).__name__}, message: {str(e)}")
                            logger.error(f"Falling back to non-streaming mode")
                            if serving_endpoint_name in streaming_support_cache['endpoints']:
                                logger.info(f"Updating cache to mark endpoint as non-streaming")
                                streaming_support_cache['endpoints'][serving_endpoint_name].update({
                                    'supports_streaming': False,
                                    'last_checked': datetime.now()
                                })
                            
                            request_data["stream"] = False
                            # Add a random query parameter to avoid any caching
                            url = f"{endpoint_url}?nocache={uuid.uuid4()}"
                            logger.info(f"Making fallback request with fresh connection to {url}")
                            async for response_chunk in streaming_handler.handle_non_streaming_response(
                                request_handler, url, headers, request_data, message.session_id, user_id, user_info, message_handler
                            ):
                                yield response_chunk
                        

        logger.info("Returning StreamingResponse")
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

    except Exception as e:
        logger.error(f"Unhandled exception in chat endpoint: {type(e).__name__}: {str(e)}")
        logger.error(f"Exception details", exc_info=True)
        
        # Handle rate limit errors specifically
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
            logger.warning("Rate limit error encountered")
            error_message = "The service is currently experiencing high demand. Please wait a moment and try again."
        
        error_message = message_handler.create_error_message(
            session_id=message.session_id,
            user_id=user_id,
            error_content="An error occurred while processing your request. " + str(e)
        )
        logger.info(f"Created error message: {error_message.message_id}")
        
        async def error_generate():
            yield f"data: {error_message.model_dump_json()}\n\n"
            yield "event: done\ndata: {}\n\n"
            
        return StreamingResponse(
            error_generate(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

# WebSocket endpoint for chat to bypass proxy timeouts
@api_app.websocket("/chat-ws")
async def websocket_chat(
    websocket: WebSocket,
    chat_db: ChatDatabase = Depends(get_chat_db),
    chat_history_cache: ChatHistoryCache = Depends(get_chat_history_cache),
    message_handler: MessageHandler = Depends(get_message_handler),
    streaming_handler: StreamingHandler = Depends(get_streaming_handler),
    request_handler: RequestHandler = Depends(get_request_handler),
    streaming_semaphore: asyncio.Semaphore = Depends(get_streaming_semaphore),
    request_queue: asyncio.Queue = Depends(get_request_queue),
    streaming_support_cache: dict = Depends(get_streaming_support_cache)
):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Get token from WebSocket headers (set by proxy during handshake)
        headers_dict = dict(websocket.headers)
        token = headers_dict.get('x-forwarded-access-token')
        
        if token and token.strip():
            actual_token = token.strip()
            logger.info(f"WebSocket using X-Forwarded-Access-Token")
        else:
            # Fallback to LOCAL_API_TOKEN environment variable
            env_token = os.environ.get("LOCAL_API_TOKEN")
            if env_token and env_token.strip():
                actual_token = env_token.strip()
                logger.info(f"WebSocket: No X-Forwarded-Access-Token header found, using LOCAL_API_TOKEN")
            else:
                logger.warning(f"WebSocket: No authentication token found in headers or LOCAL_API_TOKEN.")
                await websocket.close(code=1008, reason="No authentication token provided")
                return
            
        headers = {"Authorization": f"Bearer {actual_token}"}
        
        # Call get_user_info properly - it expects to use dependency injection
        try:
            w = WorkspaceClient(token=actual_token, auth_type="pat")
            current_user = w.current_user.me()
            user_info = {
                "email": current_user.user_name,
                "user_id": current_user.id,
                "username": current_user.user_name,
                "displayName": current_user.display_name
            }
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
            
        user_id = user_info["user_id"]
        logger.info(f"WebSocket authenticated for user_id: {user_id}")
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            logger.info(f"WebSocket received message: {data}")
            
            message_request = MessageRequest(**data)
            logger.info(f"Processing WebSocket message for session_id: {message_request.session_id}")
            
            is_first_message = chat_db.is_first_message(message_request.session_id, user_id)
            user_message = message_handler.create_message(
                message_id=str(uuid.uuid4()),
                content=message_request.content,
                role="user",
                session_id=message_request.session_id,
                user_id=user_id,
                user_info=user_info,
                is_first_message=is_first_message
            )
            
            # Load chat history with caching
            chat_history = await load_chat_history(message_request.session_id, user_id, is_first_message, chat_history_cache, chat_db)
            
            # Use longer timeout since WebSocket bypasses proxy timeout
            streaming_timeout = httpx.Timeout(
                connect=10.0,
                read=300.0,  # 5 minutes
                write=10.0,
                pool=10.0
            )
            
            serving_endpoint_name = SERVING_ENDPOINT_NAME
            endpoint_url = f"https://{DATABRICKS_HOST}/serving-endpoints/{serving_endpoint_name}/invocations"
            
            supports_streaming = await check_endpoint_capabilities(serving_endpoint_name, streaming_support_cache)
            request_data = {
                "input": [
                    *([{"role": msg["role"], "content": msg["content"]} for msg in chat_history[:-1]] 
                        if message_request.include_history else []),
                    {"role": "user", "content": message_request.content}
                ],
                "stream": True
            }
            request_data["databricks_options"] = {"return_trace": True}
            

            async with streaming_semaphore:
                async with httpx.AsyncClient(timeout=streaming_timeout) as streaming_client:
                    try:
                        logger.info("Making streaming request to Databricks")
                        async with streaming_client.stream('POST', 
                            endpoint_url,
                            headers=headers,
                            json=request_data,
                            timeout=streaming_timeout
                        ) as response:
                            
                            if response.status_code != 200:
                                raise Exception(f"HTTP {response.status_code}: {await response.aread()}")
                            
                            assistant_message_id = str(uuid.uuid4())
                            start_time = time.time()
                            first_token_time = None
                            accumulated_content = ""
                            
                            # Process raw streaming response directly without transformation
                            async for raw_line in response.aiter_lines():
                                logger.info(f"WebSocket received raw line: {raw_line}")
                                
                                # Parse SSE data and send raw JSON over WebSocket
                                if raw_line.startswith('data: '):
                                    json_data = raw_line[6:].strip()
                                    if json_data and json_data != '{}' and json_data != '[DONE]':
                                        try:
                                            raw_data = json.loads(json_data)
                                            logger.info(f"WebSocket sending raw data: {raw_data}")
                                            
                                            # Accumulate content for saving to database
                                            if raw_data.get('type') == 'response.output_text.delta' and 'delta' in raw_data:
                                                accumulated_content += raw_data['delta']
                                            elif raw_data.get('type') == 'response.output_item.done' and raw_data.get('item', {}).get('content'):
                                                # Use the final complete content if available
                                                if raw_data['item']['content'] and len(raw_data['item']['content']) > 0:
                                                    final_content = raw_data['item']['content'][0].get('text', '')
                                                    if final_content and len(final_content) > len(accumulated_content):
                                                        accumulated_content = final_content
                                            
                                            await websocket.send_json(raw_data)
                                        except json.JSONDecodeError as e:
                                            logger.error(f"JSON decode error: {e}")
                                    elif json_data == '[DONE]':
                                        logger.info("WebSocket received [DONE], ending stream")
                                        
                                        # Save the accumulated assistant response to database
                                        if accumulated_content:
                                            try:
                                                assistant_message = message_handler.create_message(
                                                    message_id=assistant_message_id,
                                                    content=accumulated_content,
                                                    role="assistant",
                                                    session_id=message_request.session_id,
                                                    user_id=user_id,
                                                    user_info=user_info,
                                                    sources=None,  # TODO: extract sources if available
                                                    metrics={'totalTime': time.time() - start_time}
                                                )
                                            except Exception as e:
                                                logger.error(f"Failed to save assistant message: {str(e)}")
                                        
                                        break
                    except Exception as e:
                        logger.error(f"WebSocket streaming error: {str(e)}")
                        await websocket.send_json({
                            'type': 'error',
                            'message': f"Streaming error: {str(e)}"
                        })
                    finally:
                        pass
                            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                'type': 'error',
                'message': f"An error occurred: {str(e)}"
            })
        except:
            pass

@api_app.get("/chats", response_model=ChatHistoryResponse)
async def get_chat_history(user_info: dict = Depends(get_user_info),chat_db: ChatDatabase = Depends(get_chat_db)):
    user_id = user_info["user_id"]
    return chat_db.get_chat_history(user_id)

# Add logout endpoint
@api_app.get("/logout")
async def logout():
    return RedirectResponse(url=f"https://{os.getenv('DATABRICKS_HOST')}/login.html", status_code=303)

@api_app.get("/user-info")
async def login(
    user_info: dict = Depends(get_user_info),
):
    """Login endpoint for PAT authentication"""
    try:
       return user_info
    except Exception as e:
        logger.error(f"Login failed with error: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
