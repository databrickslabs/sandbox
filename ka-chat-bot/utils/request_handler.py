import os
import httpx
import backoff
import asyncio
import logging
import json
import time
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime
from .config import (
    DATABRICKS_HOST,
    MAX_CONCURRENT_STREAMS,
    MAX_QUEUE_SIZE
)
from fastapi import HTTPException, Request
logger = logging.getLogger(__name__)

class RequestHandler:
    def __init__(self, endpoint_name: str):
        self.host = DATABRICKS_HOST
        self.endpoint_name = endpoint_name
        self.request_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.streaming_semaphore = asyncio.Semaphore(MAX_CONCURRENT_STREAMS)

    async def request_worker(self):
        while True:
            try:
                fut, args, kwargs = await self.request_queue.get()
                try:
                    result = await self.make_databricks_request(*args, **kwargs)
                    if not fut.done():
                        fut.set_result(result)
                except Exception as e:
                    logger.error(f"Error in request worker: {str(e)}")
                    if not fut.done():
                        fut.set_exception(e)
                finally:
                    self.request_queue.task_done()
            except Exception as e:
                logger.error(f"Critical error in request worker: {str(e)}")
                await asyncio.sleep(1)  # Add delay before retrying

    async def enqueue_request(self,*args, **kwargs):
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        await self.request_queue.put((fut, args, kwargs))
        try:
            return await fut
        except Exception as e:
            logger.error(f"Error in enqueue_request: {str(e)}")
            raise

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, httpx.ReadTimeout, httpx.HTTPStatusError, RuntimeError),
        max_tries=5,  
        max_time=120,  
        base=4,
        jitter=backoff.full_jitter,
    )
    async def make_databricks_request(self, url: str, headers: dict, data: dict):
        try:
            logger.info(f"Making Databricks request to {url}")
            
            # Create a new client for each attempt to ensure fresh connection
            async with httpx.AsyncClient(timeout=30.0) as new_client:
                response = await new_client.post(url, headers=headers, json=data, timeout=30.0)
                
                # Handle rate limit error specifically
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                        logger.info(f"Rate limited. Waiting {wait_time} seconds before retry.")
                        await asyncio.sleep(wait_time)
                    raise httpx.HTTPStatusError("Rate limit exceeded", request=response.request, response=response)
                return response
                
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise  # Re-raise the exception to trigger backoff

    # TODO: this is wrong, do we need this??
    async def extract_sources_from_trace(self, data: dict) -> list:
        """Extract sources from the Databricks API trace data format."""
        sources = []
        try:
            if data and "databricks_output" in data and "trace" in data["databricks_output"]:
                trace = data["databricks_output"]["trace"]
                if trace and "data" in trace and "spans" in trace["data"]:
                    for span in trace["data"]["spans"]:
                        if span.get("name") == "RETRIEVER":
                            outputs = span.get("attributes", {}).get("mlflow.spanOutputs")
                            if outputs:
                                try:
                                    docs = json.loads(outputs)
                                    for doc in docs:
                                        sources.append({
                                            "page_content": doc.get("page_content"),
                                            "metadata": doc.get("metadata")
                                        })
                                except Exception as e:
                                    logger.error(f"Failed to parse spanOutputs: {e}")
        except Exception as e:
            logger.error(f"Error extracting sources from trace: {e}")
        return sources

    async def handle_databricks_response(
        self,
        response: httpx.Response,
        start_time: float
    ) -> Optional[str]:
        """
        Handle Databricks API response.
        Returns (success, response_string)
        """
        total_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            sources = await self.extract_sources_from_trace(data)
            
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                response_data = {
                    'content': content,
                    'sources': sources,
                    'metrics': {'totalTime': total_time}
                }
            elif 'messages' in data and len(data['messages']) > 0:
                messages = data['messages']
                content = []
                for message in messages:
                    if message.get('role') == 'assistant' and 'content' in message:
                        content.append(message['content'])
                response_data = {
                    'content': '\n\n'.join(content),
                    'sources': sources,
                    'metrics': {'totalTime': total_time}
                }
            elif 'output' in data and len(data['output']) > 0:
                # New Responses API format
                output_item = data['output'][0]
                if output_item.get('type') == 'message' and 'content' in output_item:
                    content_items = output_item['content']
                    content = ''
                    for content_item in content_items:
                        if content_item.get('type') == 'output_text':
                            content = content_item.get('text', '')
                            break
                    response_data = {
                        'content': content,
                        'sources': sources,
                        'metrics': {'totalTime': total_time}
                    }
                else:
                    response_data = {
                        'content': 'No content found in response',
                        'sources': sources,
                        'metrics': {'totalTime': total_time}
                    }
            else:
                response_data = {
                    'content': 'No content found in response',
                    'sources': sources,
                    'metrics': {'totalTime': total_time}
                }
        else:
            # Handle specific known cases
            error_data = response.json()
            response_data = {
                'content': error_data.get('error_code', 'Encountered an error') + ". " + error_data.get('message', 'Error processing response.'),
                'sources': [],
                'metrics': None
            }
        return response_data
    