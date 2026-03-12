import pandas as pd
import time
import os
from dotenv import load_dotenv
from typing import Dict, Any, Tuple
import logging
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")

class GenieClient:
    def __init__(self, host: str, space_id: str, token: str):
        self.host = host
        self.space_id = space_id
        self.token = token
        
        # Configure SDK with retry settings and explicit PAT auth
        config = Config(
            host=f"https://{host}",
            token=token,
            auth_type="pat",  # Explicitly set authentication type to PAT
            retry_timeout_seconds=300,  # 5 minutes total retry timeout
            max_retries=5,              # Maximum number of retries
            retry_delay_seconds=2,      # Initial delay between retries
            retry_backoff_factor=2      # Exponential backoff factor
        )
        
        self.client = WorkspaceClient(config=config)
    
    def start_conversation(self, question: str) -> Dict[str, Any]:
        """Start a new conversation with the given question"""
        response = self.client.genie.start_conversation(
            space_id=self.space_id,
            content=question
        )
        return {
            "conversation_id": response.conversation_id,
            "message_id": response.message_id
        }
    
    def send_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Send a follow-up message to an existing conversation"""
        response = self.client.genie.create_message(
            space_id=self.space_id,
            conversation_id=conversation_id,
            content=message
        )
        return {
            "message_id": response.message_id
        }

    def get_message(self, conversation_id: str, message_id: str) -> Dict[str, Any]:
        """Get the details of a specific message"""
        response = self.client.genie.get_message(
            space_id=self.space_id,
            conversation_id=conversation_id,
            message_id=message_id
        )
        return response.as_dict()

    def get_query_result(self, conversation_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Get the query result using the attachment_id endpoint"""
        response = self.client.genie.get_message_attachment_query_result(
            space_id=self.space_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id
        )
        
        # Extract data_array from the correct nested location
        data_array = []
        if hasattr(response, 'statement_response') and response.statement_response is not None:
            if (hasattr(response.statement_response, 'result') and 
                response.statement_response.result is not None):
                data_array = response.statement_response.result.data_array or []
            else:
                raise ValueError("Query execution failed: No result data available. The query may have failed or returned no data.")
        else:
            raise ValueError("Query execution failed: No statement response available from the server.")
        
        # Extract schema safely
        schema = {}
        if (hasattr(response, 'statement_response') and response.statement_response is not None and
            hasattr(response.statement_response, 'manifest') and response.statement_response.manifest is not None and
            hasattr(response.statement_response.manifest, 'schema') and response.statement_response.manifest.schema is not None):
            schema = response.statement_response.manifest.schema.as_dict()
            
        return {
            'data_array': data_array,
            'schema': schema
        }

    def execute_query(self, conversation_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Execute a query using the attachment_id endpoint"""
        response = self.client.genie.execute_query(
            space_id=self.space_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id
        )
        return response.as_dict()

    def wait_for_message_completion(self, conversation_id: str, message_id: str, timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Wait for a message to reach a terminal state (COMPLETED, ERROR, etc.).
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            message = self.get_message(conversation_id, message_id)
            status = message.get("status")
            
            if status in ["COMPLETED", "ERROR", "FAILED"]:
                return message
                
            time.sleep(poll_interval)
            
        raise TimeoutError(f"Message processing timed out after {timeout} seconds")

    def get_space(self, space_id: str) -> dict:
        """Get details of a specific Genie space."""
        response = self.client.genie.get_space(space_id=space_id)
        return response.as_dict()
    
def start_new_conversation(question: str, token: str, space_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    Start a new conversation with Genie.
    Returns: (conversation_id, response_dict)
    """
    client = GenieClient(
        host=DATABRICKS_HOST,
        space_id=space_id,
        token=token
    )

    try:
        # Start a new conversation
        response = client.start_conversation(question)
        conversation_id = response["conversation_id"]
        message_id = response["message_id"]

        # Wait for the message to complete
        complete_message = client.wait_for_message_completion(conversation_id, message_id)

        # Process the response
        result = process_genie_response(client, conversation_id, message_id, complete_message)

        return conversation_id, result

    except Exception as e:
        return None, {
            "text_response": f"Sorry, an error occurred: {str(e)}. Please try again.",
            "sql_query": None, "sql_description": None,
            "dataframe": None, "content": None, "error": str(e),
        }

def continue_conversation(conversation_id: str, question: str, token: str, space_id: str) -> Dict[str, Any]:
    """
    Send a follow-up message in an existing conversation.
    Returns: response_dict
    """
    logger.info(f"Continuing conversation {conversation_id} with question: {question[:30]}...")
    client = GenieClient(
        host=DATABRICKS_HOST,
        space_id=space_id,
        token=token
    )

    try:
        # Send follow-up message in existing conversation
        response = client.send_message(conversation_id, question)
        message_id = response["message_id"]

        # Wait for the message to complete
        complete_message = client.wait_for_message_completion(conversation_id, message_id)

        # Process the response
        return process_genie_response(client, conversation_id, message_id, complete_message)

    except Exception as e:
        # Handle specific errors
        if "429" in str(e) or "Too Many Requests" in str(e):
            error_text = "Sorry, the system is currently experiencing high demand. Please try again in a few moments."
        elif "Conversation not found" in str(e):
            error_text = "Sorry, the previous conversation has expired. Please try your query again to start a new conversation."
        else:
            logger.error(f"Error continuing conversation: {str(e)}")
            error_text = f"Sorry, an error occurred: {str(e)}"
        return {
            "text_response": error_text,
            "sql_query": None, "sql_description": None,
            "dataframe": None, "content": None, "error": str(e),
        }

def process_genie_response(client, conversation_id, message_id, complete_message) -> Dict[str, Any]:
    """
    Process the response from Genie and return all available data.
    Returns a dict with keys:
        - text_response: str or None (text attachment content)
        - sql_query: str or None (generated SQL)
        - sql_description: str or None (description of the SQL query)
        - dataframe: pd.DataFrame or None (query result data)
        - content: str or None (message content / summary)
        - error: str or None
    """
    result = {
        "text_response": None,
        "sql_query": None,
        "sql_description": None,
        "dataframe": None,
        "content": None,
        "error": None,
    }

    # Extract message-level content (summary / follow-up text)
    if "content" in complete_message:
        result["content"] = complete_message.get("content", "")

    # Extract error if present
    if "error" in complete_message:
        result["error"] = str(complete_message.get("error", ""))

    # Process all attachments to collect every piece of data
    attachments = complete_message.get("attachments", [])
    for attachment in attachments:
        attachment_id = attachment.get("attachment_id")

        # Text attachment
        if "text" in attachment and "content" in attachment["text"]:
            result["text_response"] = attachment["text"]["content"]

        # Query attachment
        if "query" in attachment:
            query_info = attachment.get("query", {})
            result["sql_query"] = query_info.get("query")
            result["sql_description"] = query_info.get("description")

            if attachment_id and result["sql_query"]:
                try:
                    query_result = client.get_query_result(conversation_id, message_id, attachment_id)
                    data_array = query_result.get("data_array", [])
                    schema = query_result.get("schema", {})
                    columns = [col.get("name") for col in schema.get("columns", [])]

                    if data_array:
                        if not columns and len(data_array) > 0:
                            columns = [f"column_{i}" for i in range(len(data_array[0]))]
                        result["dataframe"] = pd.DataFrame(data_array, columns=columns)
                except Exception as e:
                    logger.warning(f"Could not fetch query result: {e}")

    return result

def genie_query(question: str, token: str, space_id: str, conversation_id: str | None = None) -> Tuple[str | None, Dict[str, Any]]:
    """
    Main entry point for querying Genie.
    Returns: (conversation_id, response_dict)
    """
    try:
        if conversation_id:
            result = continue_conversation(conversation_id, question, token, space_id)
            return conversation_id, result
        else:
            conversation_id, result = start_new_conversation(question, token, space_id)
            return conversation_id, result

    except Exception as e:
        logger.error(f"Error in conversation: {str(e)}. Please try again.")
        return None, {
            "text_response": f"Sorry, an error occurred: {str(e)}. Please try again.",
            "sql_query": None, "sql_description": None,
            "dataframe": None, "content": None, "error": str(e),
        }

