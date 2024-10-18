"""
This module provides asynchronous batch inference capabilities for LLM API interactions.
It includes an AsyncChatClient for API communication and a BatchInferenceManager for handling batch processing.
"""
import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx
from mlflow.utils.databricks_utils import get_databricks_host_creds
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_random_exponential)

from .utils import setup_logger


@dataclass
class BatchInferenceRequest:
    """
    A class to represent a single request in a batch inference process.

    Attributes:
        index (int): The index of the request in the batch.
        text (str): The input text for the inference.
        system_message (str): The system message to guide the model's behavior.
        few_shots (Optional[List[Dict[str, str]]]): Optional few-shot examples for the model.
    """
    index: int
    text: str
    system_message: str
    few_shots: Optional[List[Dict[str, str]]] = field(default=None)


@dataclass
class BatchInferenceResponse:
    """
    A class to represent a single response from a batch inference process.

    Attributes:
        index (int): The index of the response, corresponding to the request index.
        content (Optional[str]): The generated content from the model, if successful.
        token_count (int): The number of tokens used in the response.
        error (Optional[str]): Any error message, if an error occurred during processing.
    """
    index: int
    content: Optional[str]
    token_count: int
    error: Optional[str]


class AsyncChatClient:
    """
    Asynchronous client for interacting with a chat-based LLM API.

    This client handles API communication, including request formatting,
    error handling, and response processing. It implements a retry mechanism
    for handling transient errors and rate limiting.
    """

    def __init__(
        self,
        endpoint_name: str,
        request_params: Dict[str, Any],
        timeout: int = 300,
        max_retries_backpressure: int = 20,
        max_retries_other: int = 5,
        log_level: int = logging.INFO,
    ):
        """
        Initialize the AsyncChatClient with the given parameters.

        Args:
            endpoint_name (str): The name of the API endpoint.
            request_params (Dict[str, Any]): Additional parameters for the API request.
            timeout (int): The timeout for API requests in seconds.
            max_retries_backpressure (int): Maximum number of retries for backpressure errors.
            max_retries_other (int): Maximum number of retries for other errors.
            log_level (int): The logging level for the client.
        """
        self.client = httpx.AsyncClient(timeout=timeout)
        self.endpoint_name = endpoint_name
        self.request_params = request_params
        self.max_retries_backpressure = max_retries_backpressure
        self.max_retries_other = max_retries_other
        self.logger = setup_logger('AsyncChatClient', level=log_level)
        self.logger.info(f"Initialized AsyncChatClient with endpoint: {endpoint_name}")
        self.logger.info(f"Request parameters: {self.request_params}")

    @staticmethod
    def _is_backpressure(error: httpx.HTTPStatusError) -> bool:
        """
        Check if the error is due to backpressure (HTTP 429 or 503).

        Args:
            error (httpx.HTTPStatusError): The HTTP error to check.

        Returns:
            bool: True if the error is due to backpressure, False otherwise.
        """
        return error.response.status_code in (429, 503)

    def _get_stop_condition(self, retry_state):
        """
        Determine the stop condition for retries based on the error type.

        Args:
            retry_state: The current state of the retry mechanism.

        Returns:
            A stop condition appropriate for the current error type.
        """
        exception = retry_state.outcome.exception()
        if isinstance(exception, httpx.HTTPStatusError):
            if self._is_backpressure(exception):
                return stop_after_attempt(self.max_retries_backpressure)(retry_state)
        return stop_after_attempt(self.max_retries_other)(retry_state)

    async def predict(self, request: 'BatchInferenceRequest') -> Tuple[str, int]:
        """
        Send a prediction request to the API and process the response.

        This method handles the main communication with the API, including
        error handling and retries for transient failures.

        Args:
            request (BatchInferenceRequest): The request object containing
                the input for the prediction.

        Returns:
            Tuple[str, int]: A tuple containing the generated content and
                the total number of tokens used.

        Raises:
            httpx.HTTPStatusError: If an HTTP error occurs that can't be resolved by retrying.
            Exception: For any other unexpected errors.
        """
        @retry(
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            stop=lambda rs: self._get_stop_condition(rs),
            wait=wait_random_exponential(multiplier=1, max=20),
        )
        async def _predict_with_retry():
            try:
                credentials = get_databricks_host_creds("databricks")
                url = f"{credentials.host}/serving-endpoints/{self.endpoint_name}/invocations"
                headers = {
                    "Authorization": f"Bearer {credentials.token}",
                    "Content-Type": "application/json",
                }

                messages = self._initialize_messages(request)
                self.logger.debug(f"Initialized messages for request {request.index}: "
                                  f"{json.dumps(messages, ensure_ascii=False)}")

                total_content = ""
                total_tokens = 0

                while True:
                    self.logger.info(f"Sending request for index: {request.index}")
                    response = await self.client.post(
                        url=url,
                        headers=headers,
                        json={"messages": messages, **self.request_params},
                    )
                    self.logger.info(f"Received response for index: {request.index}, status: {response.status_code}")
                    response.raise_for_status()
                    response_data = response.json()

                    content = response_data["choices"][0]["message"]["content"]
                    finish_reason = response_data["choices"][0]["finish_reason"]
                    total_content += content
                    current_tokens = response_data["usage"]["total_tokens"]
                    total_tokens += current_tokens
                    
                    self.logger.info(f"Processed content for index {request.index}. "
                                    f"Finish reason: {finish_reason}, "
                                    f"Current response tokens: {current_tokens}, "
                                    f"Cumulative total tokens: {total_tokens}")

                    if finish_reason != "length":
                        break

                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": "Please continue."})

                return total_content, total_tokens

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error in predict for index {request.index}: {str(e)}")
                raise  # Re-raise to trigger retry
            except Exception as e:
                self.logger.error(f"Unexpected error in predict for index {request.index}: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise  # Re-raise unexpected errors without retry

        return await _predict_with_retry()

    def _initialize_messages(self, request: 'BatchInferenceRequest') -> List[Dict[str, str]]:
        """
        Initialize the message list with system message, few-shot examples, and user message.

        Args:
            request (BatchInferenceRequest): The request object containing
                the input data.

        Returns:
            List[Dict[str, str]]: A list of message dictionaries ready for API submission.
        """
        messages = []
        if request.system_message:
            messages.append({"role": "system", "content": request.system_message})
        if request.few_shots:
            messages.extend(request.few_shots)
        messages.append({"role": "user", "content": request.text})
        return messages

    async def close(self) -> None:
        """
        Close the underlying HTTP client.

        This method should be called when the client is no longer needed
        to ensure proper resource cleanup.
        """
        await self.client.aclose()
        self.logger.info("Closed AsyncChatClient")


class BatchInferenceManager:
    """
    Manages batch inference processing for multiple texts using AsyncChatClient.
    """

    def __init__(
        self,
        client: AsyncChatClient,
        concurrency: int = 10,
        logging_interval: int = 1,
        log_level: int = logging.INFO
    ):
        """
        Initialize the BatchInferenceManager.

        Args:
            client (AsyncChatClient): The AsyncChatClient instance to use for predictions.
            concurrency (int): The number of concurrent requests allowed.
            logging_interval (int): The interval for logging progress.
            log_level (int): The logging level for the manager.
        """
        self.client = client
        self.concurrency = concurrency
        self.logging_interval = logging_interval
        self.logger = setup_logger('BatchInferenceManager', level=log_level)
        self.logger.info(f"Initialized BatchInferenceManager with concurrency: {concurrency}")

    async def _generate(self, i: int, request: BatchInferenceRequest,
                        semaphore: asyncio.Semaphore, counter: 'AsyncCounter',
                        start_time: float) -> BatchInferenceResponse:
        """
        Generate a response for a single text input.

        Args:
            i (int): The iteration number.
            request (BatchInferenceRequest): The request data containing text, system message, and few-shots.
            semaphore (asyncio.Semaphore): Semaphore for controlling concurrency.
            counter (AsyncCounter): Counter for tracking progress.
            start_time (float): The start time of the batch process.

        Returns:
            BatchInferenceResponse: The response object containing the result or error information.
        """
        async with semaphore:
            try:
                self.logger.info(f"Starting generation for request {i} (index {request.index})")
                content, num_tokens = await self.client.predict(request)
                response = BatchInferenceResponse(index=request.index, content=content,
                                                  token_count=num_tokens, error=None)
                self.logger.info(f"Completed generation for request {i} (index {request.index})")
            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error in generation for request {i} (index {request.index}): {str(e)}")
                response = BatchInferenceResponse(index=request.index, content=None, token_count=0, error=str(e))
            except httpx.RequestError as e:
                self.logger.error(f"Request error in generation for request {i} (index {request.index}): {str(e)}")
                response = BatchInferenceResponse(index=request.index, content=None, token_count=0, error=str(e))
            except Exception as e:
                self.logger.error(f"Unexpected error in generation for request {i} (index {request.index}): {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                response = BatchInferenceResponse(index=request.index, content=None, token_count=0, error=str(e))

            await counter.increment()
            if counter.value % self.logging_interval == 0:
                elapsed_time = time.time() - start_time
                self.logger.info(f"Processed total {counter.value} requests in {elapsed_time:.2f} seconds.")
            return response

    async def batch_inference(self, requests: List[BatchInferenceRequest]) -> List[BatchInferenceResponse]:
        """
        Perform batch inference on a list of requests.

        Args:
            requests (List[BatchInferenceRequest]): A list of BatchInferenceRequest objects for each input.

        Returns:
            List[BatchInferenceResponse]: A list of BatchInferenceResponse objects containing the results.
        """
        self.logger.info(f"Starting batch inference for {len(requests)} requests")
        semaphore = asyncio.Semaphore(self.concurrency)
        counter = AsyncCounter()
        start_time = time.time()

        tasks = [self._generate(i, request, semaphore, counter, start_time)
                 for i, request in enumerate(requests)]
        responses = await asyncio.gather(*tasks)
        await self.client.close()

        self.logger.info(f"Completed batch inference for {len(requests)} requests")
        return responses


class AsyncCounter:
    """A simple asynchronous counter."""

    def __init__(self):
        self.value = 0

    async def increment(self):
        """Increment the counter value."""
        self.value += 1
