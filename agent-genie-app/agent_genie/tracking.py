import requests
import json
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get Databricks workspace URL and access token as fallbacks
fallback_workspace_url = os.getenv("WORKSPACE_URL")
fallback_access_token = os.getenv("ACCESS_TOKEN")

def create_user_interaction_table(catalog_name="user", schema_name="nitin_aggarwal", workspace_url=None, access_token=None):
    """
    Creates a table to track user interactions with the genie space
    
    Args:
        catalog_name (str): The name of the catalog (default: "users")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL. If not provided, uses fallback from environment.
        access_token (str, optional): Databricks access token. If not provided, uses fallback from environment.
        
    Returns:
        dict: Result of table creation operation
    """
    try:
        # Use provided values or fallback to environment variables
        current_workspace_url = workspace_url if workspace_url else fallback_workspace_url
        current_access_token = access_token if access_token else fallback_access_token
        
        if not current_workspace_url or not current_access_token:
            return {
                "success": False,
                "error": "Workspace URL and Access Token are required"
            }
        
        # Ensure workspace URL ends with a slash
        if not current_workspace_url.endswith('/'):
            current_workspace_url = current_workspace_url + '/'
            
        # Endpoint for SQL statements
        endpoint = f"{current_workspace_url}api/2.0/sql/statements/"
        
        # SQL to create the user interaction tracking table
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.user_interactions (
                interaction_id STRING,
                timestamp TIMESTAMP,
                user_email STRING,
                user_question STRING,
                genie_space_id STRING,
                ai_function_type STRING,
                query_classification STRING,
                conversation_id STRING,
                required_columns STRING,
                workspace_url STRING,
                response_type STRING,
                is_helpful BOOLEAN,
                feedback_reason STRING
            )
            USING DELTA
            COMMENT 'Tracks user interactions with the Databricks Genie space including feedback'
        """
        
        # Payload for the SQL statement
        payload = {
            "warehouse_id": "",  # Using the same warehouse ID from the example
            "catalog": catalog_name,
            "schema": schema_name,
            "statement": create_table_sql
        }
        
        # Headers for authentication
        headers = {
            "Authorization": f"Bearer {current_access_token}",
            "Content-Type": "application/json"
        }
        
        # Execute the SQL statement
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"User interactions table created successfully in {catalog_name}.{schema_name}")
            return {
                "success": True,
                "message": f"Table {catalog_name}.{schema_name}.user_interactions created successfully",
                "response": response.json()
            }
        else:
            logger.error(f"Error creating table: {response.text}")
            return {
                "success": False,
                "error": f"Failed to create table: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Exception occurred while creating user interactions table")
        return {
            "success": False,
            "error": str(e)
        }

def log_user_interaction(user_question, genie_space_id, ai_function_type=None, query_classification=None, 
                        conversation_id=None, required_columns=None, response_type=None,
                        is_helpful=None, feedback_reason=None, user_email=None,
                        catalog_name="users_trial", schema_name="nitin_aggarwal", 
                        workspace_url=None, access_token=None):
    """
    Logs a user interaction to the tracking table
    
    Args:
        user_question (str): The user's question
        genie_space_id (str): The genie space ID being used
        ai_function_type (str, optional): The AI function type used (e.g., ai_classify, ai_forecast)
        query_classification (str, optional): Query classification (Normal SQL, Predictive SQL, etc.)
        conversation_id (str, optional): Conversation ID for tracking sessions
        required_columns (list, optional): List of required columns
        response_type (str, optional): Type of response (table, text, etc.)
        is_helpful (bool, optional): Whether the user found the response helpful
        feedback_reason (str, optional): Reason provided when answer wasn't helpful
        user_email (str, optional): Email address of the user
        catalog_name (str): The name of the catalog (default: "users_trial")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL
        access_token (str, optional): Databricks access token
        
    Returns:
        dict: Result of the logging operation
    """
    try:
        # Use provided values or fallback to environment variables
        current_workspace_url = workspace_url if workspace_url else fallback_workspace_url
        current_access_token = access_token if access_token else fallback_access_token
        
        if not current_workspace_url or not current_access_token:
            return {
                "success": False,
                "error": "Workspace URL and Access Token are required"
            }
        
        # Ensure workspace URL ends with a slash
        if not current_workspace_url.endswith('/'):
            current_workspace_url = current_workspace_url + '/'
            
        # Generate unique interaction ID
        interaction_id = str(uuid.uuid4())
        
        # Current timestamp
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert required_columns list to JSON string if provided
        required_columns_json = json.dumps(required_columns) if required_columns else None
        
        # Escape single quotes in the question and email for SQL
        escaped_question = user_question.replace("'", "''") if user_question else ""
        escaped_user_email = user_email.replace("'", "''") if user_email else ""
        
        # Handle feedback_reason properly for SQL
        if feedback_reason is None:
            feedback_reason_sql = "NULL"
        else:
            escaped_feedback_reason = feedback_reason.replace("'", "''")
            feedback_reason_sql = f"'{escaped_feedback_reason}'"
        
        # Endpoint for SQL statements
        endpoint = f"{current_workspace_url}api/2.0/sql/statements/"
        
        # SQL to insert the interaction record
        insert_sql = f"""
            INSERT INTO {catalog_name}.{schema_name}.user_interactions 
            (interaction_id, timestamp, user_email, user_question, genie_space_id, ai_function_type, 
             query_classification, conversation_id, required_columns, workspace_url, response_type,
             is_helpful, feedback_reason)
            VALUES (
                '{interaction_id}',
                '{current_timestamp}',
                '{escaped_user_email}',
                '{escaped_question}',
                '{genie_space_id}',
                '{ai_function_type or ""}',
                '{query_classification or ""}',
                '{conversation_id or ""}',
                '{required_columns_json or ""}',
                '{current_workspace_url}',
                '{response_type or ""}',
                {str(is_helpful).lower() if is_helpful is not None else 'null'},
                {feedback_reason_sql}
            )
        """
        
        # Payload for the SQL statement
        payload = {
            "warehouse_id": "63bf73769cfb22e3",  # Using the same warehouse ID from the example
            "catalog": catalog_name,
            "schema": schema_name,
            "statement": insert_sql
        }
        
        # Headers for authentication
        headers = {
            "Authorization": f"Bearer {current_access_token}",
            "Content-Type": "application/json"
        }
        
        # Execute the SQL statement
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"User interaction logged successfully. ID: {interaction_id}")
            return {
                "success": True,
                "message": "User interaction logged successfully",
                "interaction_id": interaction_id,
                "response": response.json()
            }
        else:
            logger.error(f"Error logging user interaction: {response.text}")
            return {
                "success": False,
                "error": f"Failed to log interaction: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Exception occurred while logging user interaction")
        return {
            "success": False,
            "error": str(e)
        }

def update_user_feedback(interaction_id, is_helpful, feedback_reason=None,
                        catalog_name="users_trial", schema_name="nitin_aggarwal", 
                        workspace_url=None, access_token=None):
    """
    Updates user feedback for an existing interaction
    
    Args:
        interaction_id (str): The interaction ID to update feedback for
        is_helpful (bool): Whether the user found the response helpful
        feedback_reason (str, optional): Reason provided when answer wasn't helpful
        catalog_name (str): The name of the catalog (default: "users_trial")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL. If not provided, uses fallback from environment.
        access_token (str, optional): Databricks access token. If not provided, uses fallback from environment.
        
    Returns:
        dict: Result of the update operation
    """
    try:
        # Use provided values or fallback to environment variables
        current_workspace_url = workspace_url if workspace_url else fallback_workspace_url
        current_access_token = access_token if access_token else fallback_access_token
        
        if not current_workspace_url or not current_access_token:
            return {
                "success": False,
                "error": "Workspace URL and Access Token are required"
            }
        
        # Ensure workspace URL ends with a slash
        if not current_workspace_url.endswith('/'):
            current_workspace_url = current_workspace_url + '/'
            
        # Handle feedback_reason properly for SQL
        if feedback_reason is None:
            # Use NULL for database
            feedback_reason_sql = "NULL"
        else:
            # Escape single quotes for SQL
            escaped_feedback_reason = feedback_reason.replace("'", "''")
            feedback_reason_sql = f"'{escaped_feedback_reason}'"
            
        # Endpoint for SQL statements
        endpoint = f"{current_workspace_url}api/2.0/sql/statements/"
        
        # SQL to update the feedback for the interaction
        update_sql = f"""
            UPDATE {catalog_name}.{schema_name}.user_interactions 
            SET is_helpful = {str(is_helpful).lower()},
                feedback_reason = {feedback_reason_sql}
            WHERE interaction_id = '{interaction_id}'
        """
        
        # Payload for the SQL statement
        payload = {
            "warehouse_id": "63bf73769cfb22e3",  # Using the same warehouse ID from the example
            "catalog": catalog_name,
            "schema": schema_name,
            "statement": update_sql
        }
        
        # Headers for authentication
        headers = {
            "Authorization": f"Bearer {current_access_token}",
            "Content-Type": "application/json"
        }
        
        # Execute the SQL statement
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"User feedback updated successfully for interaction: {interaction_id}")
            return {
                "success": True,
                "message": "User feedback updated successfully",
                "interaction_id": interaction_id,
                "response": response.json()
            }
        else:
            logger.error(f"Error updating feedback: {response.text}")
            return {
                "success": False,
                "error": f"Failed to update feedback: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Exception occurred while updating user feedback")
        return {
            "success": False,
            "error": str(e)
        }

def log_user_feedback(interaction_id, is_helpful, feedback_reason=None, user_query=None, 
                     genie_response_type=None, catalog_name="users_trial", schema_name="nitin_aggarwal", 
                     workspace_url=None, access_token=None):
    """
    Updates user feedback for a specific interaction (wrapper function for backward compatibility)
    
    Args:
        interaction_id (str): The interaction ID this feedback relates to
        is_helpful (bool): Whether the user found the response helpful
        feedback_reason (str, optional): Reason provided when answer wasn't helpful
        user_query (str, optional): The original user query (ignored - kept for compatibility)
        genie_response_type (str, optional): Type of response (ignored - kept for compatibility)
        catalog_name (str): The name of the catalog (default: "users_trial")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL
        access_token (str, optional): Databricks access token
        
    Returns:
        dict: Result of the update operation
    """
    # Call the update_user_feedback function
    result = update_user_feedback(
        interaction_id=interaction_id,
        is_helpful=is_helpful,
        feedback_reason=feedback_reason,
        catalog_name=catalog_name,
        schema_name=schema_name,
        workspace_url=workspace_url,
        access_token=access_token
    )
    
    # Add feedback_id to response for backward compatibility
    if result.get("success"):
        result["feedback_id"] = interaction_id  # Use interaction_id as feedback_id for compatibility
        
    return result

def get_feedback_stats(catalog_name="users_trial", schema_name="nitin_aggarwal", 
                      workspace_url=None, access_token=None, days=7):
    """
    Get statistics about user feedback from the tracking table
    
    Args:
        catalog_name (str): The name of the catalog (default: "users_trial")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL
        access_token (str, optional): Databricks access token
        days (int): Number of days to look back for statistics (default: 7)
        
    Returns:
        dict: Statistics about user feedback
    """
    try:
        # Use provided values or fallback to environment variables
        current_workspace_url = workspace_url if workspace_url else fallback_workspace_url
        current_access_token = access_token if access_token else fallback_access_token
        
        if not current_workspace_url or not current_access_token:
            return {
                "success": False,
                "error": "Workspace URL and Access Token are required"
            }
        
        # Ensure workspace URL ends with a slash
        if not current_workspace_url.endswith('/'):
            current_workspace_url = current_workspace_url + '/'
            
        # Endpoint for SQL statements
        endpoint = f"{current_workspace_url}api/2.0/sql/statements/"
        
        # SQL to get feedback statistics
        stats_sql = f"""
            SELECT 
                COUNT(CASE WHEN is_helpful IS NOT NULL THEN 1 END) as total_feedback,
                SUM(CASE WHEN is_helpful = true THEN 1 ELSE 0 END) as helpful_count,
                SUM(CASE WHEN is_helpful = false THEN 1 ELSE 0 END) as not_helpful_count,
                ROUND(AVG(CASE WHEN is_helpful = true THEN 1.0 ELSE 0.0 END) * 100, 2) as helpfulness_percentage,
                response_type,
                COUNT(CASE WHEN is_helpful IS NOT NULL THEN 1 END) as feedback_by_type
            FROM {catalog_name}.{schema_name}.user_interactions 
            WHERE timestamp >= CURRENT_DATE - INTERVAL {days} DAYS
              AND is_helpful IS NOT NULL
            GROUP BY response_type
            ORDER BY feedback_by_type DESC
        """
        
        # Payload for the SQL statement
        payload = {
            "warehouse_id": "63bf73769cfb22e3",  # Using the same warehouse ID from the example
            "catalog": catalog_name,
            "schema": schema_name,
            "statement": stats_sql
        }
        
        # Headers for authentication
        headers = {
            "Authorization": f"Bearer {current_access_token}",
            "Content-Type": "application/json"
        }
        
        # Execute the SQL statement
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info("Feedback statistics retrieved successfully")
            return {
                "success": True,
                "message": "Feedback statistics retrieved successfully",
                "response": response.json()
            }
        else:
            logger.error(f"Error retrieving feedback statistics: {response.text}")
            return {
                "success": False,
                "error": f"Failed to retrieve feedback statistics: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Exception occurred while retrieving feedback statistics")
        return {
            "success": False,
            "error": str(e)
        }

def get_interaction_stats(catalog_name="users_trial", schema_name="nitin_aggarwal", 
                         workspace_url=None, access_token=None, days=7):
    """
    Get statistics about user interactions from the tracking table
    
    Args:
        catalog_name (str): The name of the catalog (default: "users_trial")
        schema_name (str): The name of the schema (default: "nitin_aggarwal")
        workspace_url (str, optional): Databricks workspace URL
        access_token (str, optional): Databricks access token
        days (int): Number of days to look back for statistics (default: 7)
        
    Returns:
        dict: Statistics about user interactions
    """
    try:
        # Use provided values or fallback to environment variables
        current_workspace_url = workspace_url if workspace_url else fallback_workspace_url
        current_access_token = access_token if access_token else fallback_access_token
        
        if not current_workspace_url or not current_access_token:
            return {
                "success": False,
                "error": "Workspace URL and Access Token are required"
            }
        
        # Ensure workspace URL ends with a slash
        if not current_workspace_url.endswith('/'):
            current_workspace_url = current_workspace_url + '/'
            
        # Endpoint for SQL statements
        endpoint = f"{current_workspace_url}api/2.0/sql/statements/"
        
        # SQL to get interaction statistics
        stats_sql = f"""
            SELECT 
                COUNT(*) as total_interactions,
                COUNT(DISTINCT genie_space_id) as unique_spaces,
                COUNT(DISTINCT conversation_id) as unique_conversations,
                ai_function_type,
                query_classification,
                COUNT(*) as count
            FROM {catalog_name}.{schema_name}.user_interactions 
            WHERE timestamp >= CURRENT_DATE - INTERVAL {days} DAYS
            GROUP BY ai_function_type, query_classification
            ORDER BY count DESC
        """
        
        # Payload for the SQL statement
        payload = {
            "warehouse_id": "63bf73769cfb22e3",  # Using the same warehouse ID from the example
            "catalog": catalog_name,
            "schema": schema_name,
            "statement": stats_sql
        }
        
        # Headers for authentication
        headers = {
            "Authorization": f"Bearer {current_access_token}",
            "Content-Type": "application/json"
        }
        
        # Execute the SQL statement
        response = requests.post(endpoint, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info("Interaction statistics retrieved successfully")
            return {
                "success": True,
                "message": "Statistics retrieved successfully",
                "response": response.json()
            }
        else:
            logger.error(f"Error retrieving statistics: {response.text}")
            return {
                "success": False,
                "error": f"Failed to retrieve statistics: {response.text}"
            }
            
    except Exception as e:
        logger.exception("Exception occurred while retrieving interaction statistics")
        return {
            "success": False,
            "error": str(e)
        }

# Example usage and testing
if __name__ == "__main__":
    # Create the interaction table (now includes feedback columns)
    result = create_user_interaction_table()
    print("Interaction table creation result:", result)
    
    # Log a sample interaction
    if result.get("success"):
        log_result = log_user_interaction(
            user_question="What is the total number of patients?",
            genie_space_id="01f02f3e242515679535b61b717a4d5e",
            ai_function_type="Normal SQL",
            query_classification="Normal SQL",
            conversation_id="test-conversation-1",
            required_columns=["patient_id", "first_name", "last_name"],
            response_type="table"
        )
        print("Log interaction result:", log_result)
        
        # Update feedback for the interaction
        if log_result.get("success"):
            feedback_update_result = update_user_feedback(
                interaction_id=log_result.get("interaction_id"),
                is_helpful=True,
                feedback_reason=None
            )
            print("Update feedback result:", feedback_update_result)
            
            # Test the wrapper function as well
            feedback_log_result = log_user_feedback(
                interaction_id=log_result.get("interaction_id"),
                is_helpful=False,
                feedback_reason="The answer was not detailed enough"
            )
            print("Log feedback result (wrapper):", feedback_log_result)
        
        # Get interaction statistics
        stats_result = get_interaction_stats()
        print("Interaction statistics result:", stats_result)
        
        # Get feedback statistics
        feedback_stats_result = get_feedback_stats()
        print("Feedback statistics result:", feedback_stats_result)