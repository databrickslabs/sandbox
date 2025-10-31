# Model Serving APIs

**Official Documentation**: https://databricks-sdk-py.readthedocs.io/en/latest/workspace/serving/serving_endpoints.html

Databricks Model Serving provides serverless compute for hosting ML models with automatic scaling, versioning, and monitoring. This guide covers how to list, inspect, and query serving endpoints.

## Installation

Already included in this template:
```toml
# pyproject.toml
databricks-sdk==0.59.0
```

## Setup

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError
import json
import requests

# Initialize client (uses your configured authentication)
client = WorkspaceClient()
```

## List Serving Endpoints

```python
# List all serving endpoints
try:
  endpoints = client.serving_endpoints.list()
  
  print("Available serving endpoints:")
  for endpoint in endpoints:
    print(f"Name: {endpoint.name}")
    print(f"State: {endpoint.state}")
    print(f"Creation Time: {endpoint.creation_timestamp}")
    print(f"Creator: {endpoint.creator}")
    print(f"URL: {endpoint.serving_endpoint_url}")
    print("---")
    
except DatabricksError as e:
  print(f"Error listing endpoints: {e}")
```

## Get Serving Endpoint Details

```python
# Get detailed information about a specific endpoint
def get_endpoint_details(endpoint_name: str):
  try:
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    print(f"Endpoint: {endpoint.name}")
    print(f"State: {endpoint.state}")
    print(f"URL: {endpoint.serving_endpoint_url}")
    
    # Get endpoint configuration
    if endpoint.config:
      print(f"Traffic Config:")
      for route in endpoint.config.traffic_config.routes:
        print(f"  Route: {route.served_model_name} -> {route.traffic_percentage}%")
      
      print(f"Served Models:")
      for model in endpoint.config.served_models:
        print(f"  Model: {model.name}")
        print(f"  Version: {model.model_version}")
        print(f"  Workload Size: {model.workload_size}")
        print(f"  Scale to Zero: {model.scale_to_zero_enabled}")
        if model.model_name:
          print(f"  Model Name: {model.model_name}")
    
    # Get endpoint tags
    if endpoint.tags:
      print(f"Tags: {dict(endpoint.tags)}")
    
    return endpoint
    
  except DatabricksError as e:
    print(f"Error getting endpoint details: {e}")
    return None

# Usage
endpoint_details = get_endpoint_details("my-model-endpoint")
```

## Get Endpoint Signature

```python
# Get the input/output signature of a serving endpoint
def get_endpoint_signature(endpoint_name: str):
  try:
    # Get endpoint details to find the model
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    if not endpoint.config or not endpoint.config.served_models:
      print("No served models found")
      return None
    
    # Get the primary served model
    primary_model = endpoint.config.served_models[0]
    
    print(f"Endpoint: {endpoint_name}")
    print(f"Model: {primary_model.name}")
    print(f"Version: {primary_model.model_version}")
    
    # For MLflow models, you can get signature info
    if primary_model.model_name:
      print(f"Model Name: {primary_model.model_name}")
      
      # Try to get model signature from MLflow registry
      try:
        from mlflow import MlflowClient
        mlflow_client = MlflowClient()
        
        model_version = mlflow_client.get_model_version(
          name=primary_model.model_name,
          version=primary_model.model_version
        )
        
        if model_version.run_id:
          # Get model signature from the run
          run = mlflow_client.get_run(model_version.run_id)
          signature = run.data.tags.get("mlflow.log-model.history")
          if signature:
            print(f"Model Signature: {signature}")
            
      except Exception as e:
        print(f"Could not retrieve MLflow signature: {e}")
    
    return endpoint
    
  except DatabricksError as e:
    print(f"Error getting endpoint signature: {e}")
    return None

# Usage
get_endpoint_signature("my-model-endpoint")
```

## Query Serving Endpoints

### Chat Models (Claude, GPT, etc.)

```python
# Query a chat model serving endpoint
def query_chat_endpoint(endpoint_name: str, message: str, max_tokens: int = 150, temperature: float = 0.7):
  try:
    # Import required classes
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    
    # Create proper ChatMessage objects
    messages = [
      ChatMessage(
        role=ChatMessageRole.USER,
        content=message
      )
    ]
    
    # Query the endpoint using the SDK
    response = client.serving_endpoints.query(
      name=endpoint_name,
      messages=messages,
      max_tokens=max_tokens,
      temperature=temperature
    )
    
    # Extract the answer from the response
    if response.choices and len(response.choices) > 0:
      answer = response.choices[0].message.content
      return {
        "answer": answer,
        "usage": {
          "completion_tokens": response.usage.completion_tokens,
          "prompt_tokens": response.usage.prompt_tokens,
          "total_tokens": response.usage.total_tokens
        }
      }
    else:
      return {"error": "No response received"}
    
  except DatabricksError as e:
    print(f"Error querying endpoint: {e}")
    return None

# Example usage
result = query_chat_endpoint("databricks-claude-sonnet-4", "How tall is the eiffel tower?")
print(f"Answer: {result['answer']}")
print(f"Tokens used: {result['usage']['total_tokens']}")
```

### Traditional ML Models

```python
# Query a traditional ML model serving endpoint
def query_ml_endpoint(endpoint_name: str, input_data: dict):
  try:
    # For traditional ML models, use inputs parameter
    response = client.serving_endpoints.query(
      name=endpoint_name,
      inputs=input_data
    )
    
    return response
    
  except DatabricksError as e:
    print(f"Error querying endpoint: {e}")
    return None

# Example usage for different model types
# For a simple sklearn model
sklearn_input = {
  "inputs": [[1.0, 2.0, 3.0, 4.0]]
}

# For a chat model
chat_input = {
  "messages": [
    {"role": "user", "content": "What is Databricks?"}
  ],
  "max_tokens": 100
}

# For a custom model with dataframe input
df_input = {
  "dataframe_split": {
    "columns": ["feature1", "feature2", "feature3"],
    "data": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
  }
}

# Query the endpoint
result = query_endpoint("my-model-endpoint", sklearn_input)
print(f"Result: {result}")
```

## Batch Inference

```python
# Send batch requests to a serving endpoint
def batch_query_endpoint(endpoint_name: str, batch_data: list):
  """Query endpoint with multiple inputs"""
  try:
    endpoint = client.serving_endpoints.get(endpoint_name)
    url = f"{endpoint.serving_endpoint_url}/invocations"
    
    headers = {
      "Authorization": f"Bearer {client.config.token}",
      "Content-Type": "application/json"
    }
    
    # Prepare batch input
    batch_input = {
      "dataframe_split": {
        "columns": batch_data[0]["columns"] if batch_data else [],
        "data": [item["data"] for item in batch_data]
      }
    }
    
    response = requests.post(url, json=batch_input, headers=headers)
    response.raise_for_status()
    
    return response.json()
    
  except Exception as e:
    print(f"Error in batch query: {e}")
    return None

# Example batch data
batch_data = [
  {"columns": ["feature1", "feature2"], "data": [1.0, 2.0]},
  {"columns": ["feature1", "feature2"], "data": [3.0, 4.0]},
  {"columns": ["feature1", "feature2"], "data": [5.0, 6.0]}
]

batch_result = batch_query_endpoint("my-model-endpoint", batch_data)
```

## Error Handling

```python
from databricks.sdk.errors import NotFound, PermissionDenied, BadRequest
import requests

def safe_query_endpoint(endpoint_name: str, input_data: dict):
  try:
    # Check if endpoint exists
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    if endpoint.state != "READY":
      return {"error": f"Endpoint not ready. Current state: {endpoint.state}"}
    
    # Query the endpoint
    url = f"{endpoint.serving_endpoint_url}/invocations"
    headers = {
      "Authorization": f"Bearer {client.config.token}",
      "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=input_data, headers=headers, timeout=30)
    
    if response.status_code == 200:
      return {"success": True, "result": response.json()}
    elif response.status_code == 400:
      return {"error": "Bad request - check input format", "details": response.text}
    elif response.status_code == 429:
      return {"error": "Rate limit exceeded - try again later"}
    else:
      return {"error": f"HTTP {response.status_code}: {response.text}"}
    
  except NotFound:
    return {"error": f"Endpoint '{endpoint_name}' not found"}
  except PermissionDenied:
    return {"error": "Permission denied - check endpoint access"}
  except requests.exceptions.Timeout:
    return {"error": "Request timeout - endpoint may be slow"}
  except requests.exceptions.ConnectionError:
    return {"error": "Connection error - check network"}
  except Exception as e:
    return {"error": f"Unexpected error: {str(e)}"}

# Usage with error handling
result = safe_query_endpoint("my-model-endpoint", {"inputs": [[1, 2, 3]]})
print(result)
```

## FastAPI Integration

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import asyncio
import aiohttp

router = APIRouter()

class ModelInput(BaseModel):
  inputs: List[List[float]]

class ModelOutput(BaseModel):
  predictions: List[float]
  endpoint_name: str

class BatchModelInput(BaseModel):
  inputs: List[List[List[float]]]

@router.get("/serving-endpoints")
async def list_serving_endpoints():
  """List all available serving endpoints"""
  try:
    endpoints = client.serving_endpoints.list()
    return [
      {
        "name": endpoint.name,
        "state": endpoint.state,
        "url": endpoint.serving_endpoint_url,
        "creation_time": endpoint.creation_timestamp,
        "creator": endpoint.creator
      }
      for endpoint in endpoints
    ]
  except DatabricksError as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get("/serving-endpoints/{endpoint_name}")
async def get_serving_endpoint(endpoint_name: str):
  """Get detailed information about a serving endpoint"""
  try:
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    return {
      "name": endpoint.name,
      "state": endpoint.state,
      "url": endpoint.serving_endpoint_url,
      "config": {
        "served_models": [
          {
            "name": model.name,
            "model_name": model.model_name,
            "model_version": model.model_version,
            "workload_size": model.workload_size,
            "scale_to_zero": model.scale_to_zero_enabled
          }
          for model in endpoint.config.served_models
        ] if endpoint.config else []
      },
      "tags": dict(endpoint.tags) if endpoint.tags else {}
    }
  except NotFound:
    raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_name}' not found")
  except DatabricksError as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/serving-endpoints/{endpoint_name}/predict")
async def predict(endpoint_name: str, input_data: ModelInput):
  """Query a serving endpoint with input data"""
  try:
    # Get endpoint details
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    if endpoint.state != "READY":
      raise HTTPException(
        status_code=400, 
        detail=f"Endpoint not ready. Current state: {endpoint.state}"
      )
    
    # Prepare async request
    url = f"{endpoint.serving_endpoint_url}/invocations"
    headers = {
      "Authorization": f"Bearer {client.config.token}",
      "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
      async with session.post(
        url, 
        json=input_data.model_dump(), 
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=30)
      ) as response:
        if response.status == 200:
          result = await response.json()
          return {
            "predictions": result.get("predictions", []),
            "endpoint_name": endpoint_name
          }
        else:
          error_text = await response.text()
          raise HTTPException(
            status_code=response.status,
            detail=f"Model serving error: {error_text}"
          )
    
  except NotFound:
    raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_name}' not found")
  except asyncio.TimeoutError:
    raise HTTPException(status_code=408, detail="Request timeout")
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/serving-endpoints/{endpoint_name}/batch-predict")
async def batch_predict(endpoint_name: str, batch_input: BatchModelInput):
  """Send batch prediction requests to a serving endpoint"""
  try:
    endpoint = client.serving_endpoints.get(endpoint_name)
    
    if endpoint.state != "READY":
      raise HTTPException(
        status_code=400,
        detail=f"Endpoint not ready. Current state: {endpoint.state}"
      )
    
    url = f"{endpoint.serving_endpoint_url}/invocations"
    headers = {
      "Authorization": f"Bearer {client.config.token}",
      "Content-Type": "application/json"
    }
    
    # Process batch requests
    results = []
    async with aiohttp.ClientSession() as session:
      tasks = []
      for batch_item in batch_input.inputs:
        task = session.post(
          url,
          json={"inputs": batch_item},
          headers=headers,
          timeout=aiohttp.ClientTimeout(total=30)
        )
        tasks.append(task)
      
      responses = await asyncio.gather(*tasks, return_exceptions=True)
      
      for i, response in enumerate(responses):
        if isinstance(response, Exception):
          results.append({"error": str(response), "index": i})
        else:
          async with response:
            if response.status == 200:
              result = await response.json()
              results.append({
                "predictions": result.get("predictions", []),
                "index": i
              })
            else:
              error_text = await response.text()
              results.append({
                "error": f"HTTP {response.status}: {error_text}",
                "index": i
              })
    
    return {
      "results": results,
      "endpoint_name": endpoint_name,
      "total_requests": len(batch_input.inputs)
    }
    
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

## Common Use Cases

### Real-time Inference
```python
# For real-time predictions with low latency
def real_time_predict(endpoint_name: str, features: list):
  input_data = {"inputs": [features]}
  return query_endpoint(endpoint_name, input_data)

# Usage
prediction = real_time_predict("fraud-detection", [100.0, 0.5, 1.2])
```

### Chat Model Inference
```python
# For chat/LLM models
def chat_with_model(endpoint_name: str, messages: list, max_tokens: int = 100):
  input_data = {
    "messages": messages,
    "max_tokens": max_tokens,
    "temperature": 0.7
  }
  return query_endpoint(endpoint_name, input_data)

# Usage
response = chat_with_model(
  "llama-chat-endpoint",
  [{"role": "user", "content": "Explain machine learning"}]
)
```

### Feature Store Integration
```python
# Query endpoint with feature store features
def predict_with_features(endpoint_name: str, primary_keys: dict):
  """Use feature store to get features and make predictions"""
  # This would integrate with Databricks Feature Store
  # to retrieve features and send to serving endpoint
  pass
```

## Best Practices

1. **Check endpoint state** before querying (should be "READY")
2. **Handle timeouts** gracefully for slow models
3. **Implement retry logic** for temporary failures
4. **Monitor rate limits** and implement backoff
5. **Cache endpoint details** to avoid repeated metadata calls
6. **Use async requests** for batch processing
7. **Validate input format** before sending requests
8. **Log predictions** for monitoring and debugging

## Resource Links

- **Serving Endpoints API**: https://databricks-sdk-py.readthedocs.io/en/latest/workspace/serving/serving_endpoints.html
- **Model Serving Guide**: https://docs.databricks.com/machine-learning/model-serving/index.html
- **REST API Reference**: https://docs.databricks.com/api/workspace/servingendpoints
- **MLflow Model Serving**: https://docs.databricks.com/mlflow/models.html#serve-models