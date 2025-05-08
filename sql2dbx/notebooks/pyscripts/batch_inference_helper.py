"""
This module provides asynchronous batch inference capabilities for Databricks model serving endpoints.

Key components:
- AsyncChatClient: Handles API communication with retries and error handling
- BatchInferenceManager: Manages concurrent processing of multiple requests
- BatchInferenceRequest/Response: Data structures for request/response handling
"""
import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
from httpx import codes
from tenacity import (RetryCallState, RetryError, retry,
                      retry_if_exception_type, stop_after_attempt,
                      wait_random_exponential)

from .databricks_credentials import DatabricksCredentials
from .utils import setup_logger

# Default configuration values
DEFAULT_CONCURRENCY = 10
DEFAULT_LOGGING_INTERVAL = 1
DEFAULT_MAX_RETRIES_BACKPRESSURE = 20
DEFAULT_MAX_RETRIES_OTHER = 5
DEFAULT_TIMEOUT = 300

# Retry backoff configuration
# multiplier: Base wait time in seconds for exponential backoff
# max_wait: Maximum wait time limit in seconds
# These values are fixed to ensure proper load management for Databricks endpoints
# and maintain consistent retry behavior across all requests
DEFAULT_RETRY_MULTIPLIER = 5
DEFAULT_RETRY_MAX_WAIT = 60


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
class TokenUsage:
    """
    A class to represent token usage information from an API response.

    Attributes:
        prompt_tokens (int): Number of tokens used for the prompt.
        completion_tokens (int): Number of tokens used for the completion/response.
        total_tokens (int): Total number of tokens used (prompt + completion).
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class BatchInferenceResponse:
    """
    A class to represent a single response from a batch inference process.

    Attributes:
        index (int): The index of the response, corresponding to the request index.
        content (Optional[str]): The generated content from the model, if successful.
        token_usage (Optional[TokenUsage]): Detailed token usage information.
        error (Optional[str]): Any error message, if an error occurred during processing.
        processing_time_seconds (Optional[float]): Total time in seconds spent processing this request.
    """
    index: int
    content: Optional[str]
    token_usage: Optional[TokenUsage]
    error: Optional[str]
    processing_time_seconds: Optional[float]


class BatchInferenceManager:
    """
    Manager for concurrent batch inference processing.

    Key features:
    - Controls concurrent execution
    - Monitors progress and handles errors
    - Manages response aggregation
    """

    def __init__(
        self,
        client: 'AsyncChatClient',
        concurrency: int = DEFAULT_CONCURRENCY,
        logging_interval: int = DEFAULT_LOGGING_INTERVAL,
        log_level: Union[int, str] = logging.INFO,
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
        start_time = time.perf_counter()

        tasks = [self._process_inference(request, semaphore, counter, start_time)
                 for request in requests]
        responses = await asyncio.gather(*tasks)
        await self.client.close()

        self.logger.info(f"Completed batch inference for {len(requests)} requests")
        return responses

    async def _process_inference(self, request: BatchInferenceRequest,
                                 semaphore: asyncio.Semaphore, counter: 'AsyncCounter',
                                 start_time: float) -> BatchInferenceResponse:
        """
        Process inference for a single request.

        Args:
            request (BatchInferenceRequest): The request data containing text, system message, and few-shots.
            semaphore (asyncio.Semaphore): Semaphore for controlling concurrency.
            counter (AsyncCounter): Counter for tracking progress.
            start_time (float): The start time of the batch process.

        Returns:
            BatchInferenceResponse: The response object containing the result or error information.
        """
        async with semaphore:
            try:
                self.logger.info(f"Starting inference for index {request.index}")
                predict_start_time = time.perf_counter()
                content, token_usage = await self.client.predict(request)
                processing_time_seconds = round(time.perf_counter() - predict_start_time, 2)
                response = BatchInferenceResponse(
                    index=request.index,
                    content=content,
                    token_usage=token_usage,
                    error=None,
                    processing_time_seconds=processing_time_seconds
                )
                self.logger.info(
                    f"Completed inference for index {request.index} in {processing_time_seconds:.2f} seconds")
            except Exception as e:
                response = await self._handle_error(e, request.index)

            await counter.increment()
            if counter.value % self.logging_interval == 0:
                elapsed_time = time.perf_counter() - start_time
                self.logger.info(f"Processed total {counter.value} requests in {elapsed_time:.2f} seconds.")

            return response

    async def _handle_error(self, e: Exception, request_index: int) -> BatchInferenceResponse:
        """
        Handle error during inference and create appropriate response.

        Args:
            e: The exception that occurred
            request_index: Index of the request that caused the error

        Returns:
            BatchInferenceResponse: Response with error information
        """
        # Extract original error from RetryError if possible
        if isinstance(e, RetryError) and hasattr(e, 'last_attempt') and e.last_attempt.failed:
            try:
                original_error = e.last_attempt.exception()
                if original_error:
                    e = original_error  # Replace with the original error
            except Exception:
                # Keep the original RetryError if extraction fails
                pass

        # Add response details for HTTP errors
        error_message = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            self.client._log_http_error(e, request_index, logger=self.logger)
            try:
                response_json = e.response.json()
                error_message = f"{error_message}\nResponse details: {json.dumps(response_json, ensure_ascii=False)}"
            except json.JSONDecodeError:
                try:
                    response_text = e.response.text
                    if response_text:
                        error_message = f"{error_message}\nResponse details: {response_text[:500]}"
                except Exception:
                    pass
        elif isinstance(e, httpx.RequestError):
            self.client._log_request_error(e, request_index, logger=self.logger)
        else:
            self.client._log_general_error(e, request_index, logger=self.logger)

        return BatchInferenceResponse(
            index=request_index,
            content=None,
            token_usage=None,
            error=error_message,
            processing_time_seconds=None
        )


class AsyncChatClient:
    """
    Asynchronous client for Databricks model serving endpoints.

    Key features:
    - Handles API communication with retry mechanism
    - Supports different retry strategies for backpressure
    - Provides error logging and response handling
    """

    def __init__(
        self,
        endpoint_name: str,
        request_params: Dict[str, Any],
        timeout: int = DEFAULT_TIMEOUT,
        max_retries_backpressure: int = DEFAULT_MAX_RETRIES_BACKPRESSURE,
        max_retries_other: int = DEFAULT_MAX_RETRIES_OTHER,
        log_level: Union[int, str] = logging.INFO,
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

    async def predict(self, request: 'BatchInferenceRequest') -> Tuple[str, TokenUsage]:
        """
        Send a prediction request to the API and process the response.

        This method handles the main communication with the API, including
        error handling and retries for transient failures.

        Args:
            request (BatchInferenceRequest): The request object containing
                the input for the prediction.

        Returns:
            Tuple[str, TokenUsage]: A tuple containing the generated content and
                the token usage information.

        Raises:
            httpx.HTTPStatusError: If an HTTP error occurs that can't be resolved by retrying.
            Exception: For any other unexpected errors.
        """
        @retry(
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            stop=lambda rs: self._get_stop_condition(rs),
            wait=wait_random_exponential(multiplier=DEFAULT_RETRY_MULTIPLIER, max=DEFAULT_RETRY_MAX_WAIT),
        )
        async def _predict_with_retry():
            try:
                databricks_host_and_token = DatabricksCredentials().get_host_and_token()
                databricks_host = databricks_host_and_token["host"]
                databricks_token = databricks_host_and_token["token"]

                url = f"{databricks_host}/serving-endpoints/{self.endpoint_name}/invocations"
                headers = {
                    "Authorization": f"Bearer {databricks_token}",
                    "Content-Type": "application/json",
                }

                messages = self._initialize_messages(request)
                total_content = ""
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0

                while True:
                    # Prepare the request body with the current messages
                    request_body = {"messages": messages}
                    if self.request_params:
                        request_body.update(self.request_params)
                    request_args = {
                        'url': url,
                        'headers': headers,
                        'json': request_body
                    }
                    self._log_request_args(request_args, request.index, level=logging.INFO)

                    # Send the request
                    response = await self.client.post(**request_args)
                    response.raise_for_status()
                    self._log_response_details(response, request.index, level=logging.DEBUG)

                    # Process the response data
                    response_data = response.json()
                    content = self._parse_content(response_data["choices"][0]["message"]["content"])
                    total_content += content
                    finish_reason = response_data["choices"][0]["finish_reason"]

                    # Extract token usage information
                    token_usage = response_data["usage"]
                    current_prompt_tokens = token_usage.get("prompt_tokens", 0)
                    current_completion_tokens = token_usage.get("completion_tokens", 0)
                    current_total_tokens = token_usage.get("total_tokens", 0)
                    prompt_tokens += current_prompt_tokens
                    completion_tokens += current_completion_tokens
                    total_tokens += current_total_tokens

                    self.logger.info(
                        f"Processed content for index {request.index}. "
                        f"Finish reason: {finish_reason}, "
                        f"Prompt tokens: {current_prompt_tokens}, "
                        f"Completion tokens: {current_completion_tokens}, "
                        f"Total tokens: {current_total_tokens}, "
                        f"Cumulative prompt tokens: {prompt_tokens}, "
                        f"Cumulative completion tokens: {completion_tokens}, "
                        f"Cumulative total tokens: {total_tokens}"
                    )

                    # Check if the response indicates that the model has finished
                    if finish_reason != "length":
                        break

                    # If the response indicates that the finished reason is "length",
                    # we need to continue the conversation by appending the last message
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"The previous response ended with: '{content[-50:]}'. "
                                     f"Please continue exactly from this point without repeating any content."})

                return total_content, TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )

            # Handle HTTP errors (e.g., 4xx, 5xx)
            except httpx.HTTPStatusError as e:
                self._log_http_error(e, request.index)
                raise

            # Handle non-HTTP errors (e.g., connection errors, timeouts)
            except Exception as e:
                self._log_general_error(e, request.index)
                raise

        return await _predict_with_retry()

    async def close(self) -> None:
        """
        Close the underlying HTTP client.

        This method should be called when the client is no longer needed
        to ensure proper resource cleanup.
        """
        await self.client.aclose()
        self.logger.info("Closed AsyncChatClient")

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

    @staticmethod
    def _parse_content(content: Any) -> str:
        """
        Parse the content from the API response, handling different response formats.
        Claude 3.7 Sonnet with Extended thinking enabled returns a structured response format
        where "content" field is a list of objects rather than a simple string:
        - It contains a "reasoning" object with the model's thought process
        - It also contains a "text" object with the final response text
        We need to handle both formats for compatibility

        Args:
            content: The content field from the API response, which could be either
                    a string (standard format) or a list of structured objects 
                    (Extended thinking mode with reasoning and text objects).

        Returns:
            str: The extracted text content, combining all "text" type objects in
                Extended thinking mode or returning the raw string in standard mode.

        Raises:
            TypeError: If the content format is unexpected.
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return "".join(
                content_part.get("text", "")
                for content_part in content
                if content_part.get("type") == "text"
            )
        raise TypeError(f"Unexpected content format: {type(content).__name__}")

    def _get_stop_condition(self, retry_state: RetryCallState) -> Callable[[RetryCallState], bool]:
        """
        Determine the stop condition for retries based on the error type.

        Args:
            retry_state: The current state of the retry mechanism.

        Returns:
            Callable[[RetryCallState], bool]: A stop condition function appropriate for the current error type.
        """
        exception = retry_state.outcome.exception()
        current_attempt = retry_state.attempt_number

        if isinstance(exception, httpx.HTTPStatusError):
            # Check for validation errors first - always stop immediately (no retry)
            if self._is_parameter_validation_error(exception):
                self.logger.info(
                    f"Validation error detected. Stopping retry immediately after attempt {current_attempt}."
                )
                return stop_after_attempt(1)(retry_state)

            # Then check for backpressure errors (will retry)
            elif self._is_backpressure(exception):
                max_attempts = self.max_retries_backpressure
                self.logger.info(
                    f"Backpressure error occurred (status: {exception.response.status_code}). "
                    f"Current attempt: {current_attempt}, max attempts: {max_attempts}, "
                    f"will {'stop' if current_attempt >= max_attempts else 'retry'}"
                )
                return stop_after_attempt(max_attempts)(retry_state)

            # Other HTTP errors (will retry)
            else:
                max_attempts = self.max_retries_other
                self.logger.info(
                    f"HTTP error occurred (status: {exception.response.status_code}). "
                    f"Current attempt: {current_attempt}, max attempts: {max_attempts}, "
                    f"will {'stop' if current_attempt >= max_attempts else 'retry'}"
                )
        else:
            # General non-HTTP errors (will retry)
            max_attempts = self.max_retries_other
            self.logger.info(
                f"General error occurred ({type(exception).__name__}). "
                f"Current attempt: {current_attempt}, max attempts: {max_attempts}, "
                f"will {'stop' if current_attempt >= max_attempts else 'retry'}"
            )
        return stop_after_attempt(max_attempts)(retry_state)

    def _is_parameter_validation_error(self, error: httpx.HTTPStatusError) -> bool:
        """
        Check if the error is a parameter validation error that should not be retried.

        Args:
            error: The HTTP status error

        Returns:
            bool: True if this is a validation error, False otherwise
        """
        if error.response.status_code == codes.BAD_REQUEST:
            try:
                response_data = error.response.json()
                if response_data.get("message"):
                    error_msg = str(response_data["message"]).lower()
                    # List of patterns indicating validation errors (not backpressure)
                    validation_patterns = [
                        "extra inputs are not permitted",
                        "invalid parameter",
                        "parameter validation",
                        "required parameter",
                        "missing parameter",
                        "invalid format",
                        "not a valid"
                    ]

                    for pattern in validation_patterns:
                        if pattern in error_msg:
                            self.logger.debug(
                                f"Parameter validation error detected: '{error_msg}'. "
                                f"Will not retry as this is not a backpressure issue."
                            )
                            return True
            except (json.JSONDecodeError, AttributeError):
                pass
        return False

    def _is_backpressure(self, error: httpx.HTTPStatusError) -> bool:
        """
        Check if the error is due to backpressure (HTTP 429 or 503) or
        if it's a 400 with null message from Databricks Claude endpoint.
        """
        if error.response.status_code in (codes.TOO_MANY_REQUESTS, codes.SERVICE_UNAVAILABLE):
            return True
        # Treating cases where the token limit is reached in a single inference as backpressure causes excessive retries, so it is temporarily commented out.
        # if self._is_databricks_claude_specific_backpressure(error):
        #     return True
        return False

    def _is_databricks_claude_specific_backpressure(self, error: httpx.HTTPStatusError) -> bool:
        """
        Check for Databricks Claude specific backpressure pattern:
        HTTP 400 with null message field.

        This is a temporary workaround for Databricks Claude endpoints
        that may return 400 instead of 429 for certain size-related limitations.
        """
        if (error.response.status_code == codes.BAD_REQUEST and
                "databricks-claude" in self.endpoint_name):
            try:
                response_data = error.response.json()
                if response_data.get("message") is None:
                    self.logger.warning(
                        "Databricks Claude specific backpressure detected: "
                        "400 BAD_REQUEST with null message. Treating as backpressure."
                    )
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass
        return False

    def _log_request_args(self, request_args: Dict[str, Any], request_index: int, max_head: int = 200, max_tail=100, level=logging.INFO) -> None:
        """
        Log the request arguments for debugging purposes.

        Args:
            request_args: The arguments used in the request
            request_index: Index of the request being processed
            max_head: Maximum number of characters to log from the start of the request body
            max_tail: Maximum number of characters to log from the end of the request body
            level: The logging level to use (default is INFO)
        """
        request_body = request_args.get('json', {})
        body_str = json.dumps(request_body, ensure_ascii=False)
        body_len = len(body_str)
        self.logger.log(
            level,
            f"Request for index {request_index} - Request details: "
            f"Size: {body_len} chars, "
            f"Content: {body_str[:max_head]}... [truncated] ...{body_str[-max_tail:]}"
        )

    def _log_response_details(self, response: httpx.Response, request_index: int, max_head: int = 200, max_tail: int = 100, level=logging.DEBUG) -> None:
        """
        Log the detailed response data at DEBUG level, with truncation.

        Args:
            response: The HTTP response object
            request_index: Index of the request being processed
            max_head: Maximum characters to show from the beginning for text content
            max_tail: Maximum characters to show from the end for text content
            level: The logging level to use (default is DEBUG)
        """
        try:
            # For JSON responses, use the dictionary truncation method
            log_data = self._truncate_long_strings_in_dict(response.json())
            body_content = json.dumps(log_data, ensure_ascii=False)
            content_type = "JSON"
        except json.JSONDecodeError:
            # For non-JSON responses, use simple text truncation
            body_str = response.text
            body_content = f"{body_str[:max_head]}... [truncated] ...{body_str[-max_tail:]}"
            content_type = "non-JSON"

        self.logger.log(
            level,
            f"Request for index {request_index} - Response details ({content_type}): "
            f"Status: {response.status_code}, "
            f"Headers: {dict(response.headers)}, "
            f"Body: {body_content}"
        )

    def _truncate_long_strings_in_dict(self, data, max_length: int = 2000):
        """
        Recursively truncate long string values in a dictionary or list.

        Args:
            data: The dictionary or list to process
            max_length: Maximum length for string values

        Returns:
            A copy of the data with long strings truncated
        """
        if isinstance(data, dict):
            return {k: self._truncate_long_strings_in_dict(v, max_length) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._truncate_long_strings_in_dict(item, max_length) for item in data]
        elif isinstance(data, str) and len(data) > max_length:
            # Truncate long string values
            return data[:max_length // 2] + f" ... [truncated {len(data) - max_length} chars] ... " + data[-max_length // 2:]
        else:
            return data

    def _log_http_error(self, e: httpx.HTTPStatusError, request_index: int, logger=None) -> None:
        """
        Log detailed information for HTTP errors.

        Args:
            e: The HTTP error exception
            request_index: Index of the request that caused the error
            logger: Optional logger to use instead of self.logger
        """
        logger = logger or self.logger
        logger.error(f"HTTP error in predict for index {request_index}: {str(e)}")

        # Log response body
        try:
            response_body = e.response.json()
            logger.error(f"Error response body (JSON): {json.dumps(response_body, ensure_ascii=False)}")
        except json.JSONDecodeError:
            try:
                response_body = e.response.text
                logger.error(f"Error response body (Text): {response_body[:2000]}")
            except Exception as text_err:
                logger.error(f"Failed to extract response body text: {str(text_err)}")

        # Log response headers
        try:
            logger.error(f"Response headers: {dict(e.response.headers)}")
        except Exception as header_err:
            logger.error(f"Failed to extract response headers: {str(header_err)}")

    def _log_request_error(self, e: httpx.RequestError, request_index: int, logger=None) -> None:
        """
        Log detailed information for request errors.

        Args:
            e: The request error exception
            request_index: Index of the request that caused the error
            logger: Optional logger to use instead of self.logger
        """
        logger = logger or self.logger
        logger.error(f"Request error in predict for index {request_index}: {str(e)}")

        # Log request details if available
        if hasattr(e, 'request'):
            try:
                logger.error(f"Request URL: {e.request.url}")
                logger.error(f"Request method: {e.request.method}")
            except Exception:
                pass

        logger.error(f"Traceback: {traceback.format_exc()}")

    def _log_general_error(self, e: Exception, request_index: int, logger=None) -> None:
        """
        Log detailed information for general (non-HTTP) errors.

        Args:
            e: The exception that was raised
            request_index: Index of the request that caused the error
            logger: Optional logger to use instead of self.logger
        """
        logger = logger or self.logger
        logger.error(f"Unexpected error in predict for index {request_index}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")


class AsyncCounter:
    """
    Thread-safe counter for async operations.
    """

    def __init__(self):
        self.value = 0

    async def increment(self):
        """Increment the counter value."""
        self.value += 1
