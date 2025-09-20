import os
import json
import requests
from flask import Flask, render_template, request, jsonify
from databricks.sdk.core import Config
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='static')

cfg = Config()
client = WorkspaceClient()

# Model serving endpoint name
ENDPOINT_NAME = "agents_ws_vfc_demo-sch_vfc_demo-fashion_merchandising_agent"

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests and forward to model serving endpoint using Databricks SDK"""
    try:
        # Get the message history from the request
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        # Convert messages to ChatMessage objects
        chat_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Map roles to ChatMessageRole enum
            if role == 'user':
                chat_role = ChatMessageRole.USER
            elif role == 'assistant':
                chat_role = ChatMessageRole.ASSISTANT
            elif role == 'system':
                chat_role = ChatMessageRole.SYSTEM
            else:
                chat_role = ChatMessageRole.USER  # Default to user
            
            chat_messages.append(ChatMessage(role=chat_role, content=content))
        
        # Get user information for logging
        user_email = request.headers.get('X-Forwarded-Email')
        app.logger.info(f"Making request to model endpoint for user: {user_email}")
        
        # Make request to model serving endpoint using Databricks SDK
        response = client.serving_endpoints.query(
            name=ENDPOINT_NAME,
            messages=chat_messages
        )
        
        # Extract the response content
        if response and hasattr(response, 'choices') and response.choices:
            # Get the first choice
            choice = response.choices[0]
            if hasattr(choice, 'message') and choice.message:
                result_content = choice.message.content
                return jsonify({'content': result_content})
            else:
                return jsonify({'error': 'No message content in response'}), 500
        else:
            return jsonify({'error': 'No response choices received'}), 500
            
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Error calling model endpoint: {error_msg}")
        
        # Handle specific error types
        if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return jsonify({
                'error': 'Authentication failed. Your Databricks token may have expired.',
                'details': 'Please refresh the page or log in again.'
            }), 401
        elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            return jsonify({
                'error': 'Access denied. You may not have permission to access this model endpoint.',
                'details': 'Please contact your Databricks administrator.'
            }), 403
        elif "timeout" in error_msg.lower():
            return jsonify({'error': 'Request timed out. Please try again.'}), 504
        else:
            return jsonify({
                'error': f'Unexpected error: {error_msg}',
                'details': 'Please try again or contact support if the issue persists.'
            }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    user_email = request.headers.get('X-Forwarded-Email')
    
    try:
        # Test the client connection
        client.current_user.me()
        client_healthy = True
    except Exception as e:
        client_healthy = False
        app.logger.error(f"Client health check failed: {str(e)}")
    
    return jsonify({
        'status': 'healthy',
        'client_authenticated': client_healthy,
        'user_email': user_email if user_email else 'anonymous',
        'endpoint_name': ENDPOINT_NAME
    })

@app.route('/api/debug')
def debug():
    """Debug endpoint to check authentication and endpoint status"""
    headers_info = {
        'X-Forwarded-Access-Token': 'present' if request.headers.get('X-Forwarded-Access-Token') else 'missing',
        'X-Forwarded-Email': request.headers.get('X-Forwarded-Email', 'not provided'),
        'User-Agent': request.headers.get('User-Agent', 'not provided'),
        'Authorization': 'present' if request.headers.get('Authorization') else 'missing'
    }
    
    try:
        # Check if we can access the serving endpoint
        endpoint_info = client.serving_endpoints.get(name=ENDPOINT_NAME)
        endpoint_status = endpoint_info.state.value if endpoint_info.state else 'unknown'
    except Exception as e:
        endpoint_status = f'error: {str(e)}'
    
    try:
        # Check current user
        current_user = client.current_user.me()
        user_info = current_user.user_name if current_user else 'unknown'
    except Exception as e:
        user_info = f'error: {str(e)}'
    
    return jsonify({
        'message': 'Debug information for Databricks App',
        'headers': headers_info,
        'endpoint_name': ENDPOINT_NAME,
        'endpoint_status': endpoint_status,
        'current_user': user_info,
        'sdk_config': {
            'host': cfg.host if hasattr(cfg, 'host') else 'not set',
            'auth_type': cfg.auth_type if hasattr(cfg, 'auth_type') else 'not set'
        }
    })

if __name__ == '__main__':
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)