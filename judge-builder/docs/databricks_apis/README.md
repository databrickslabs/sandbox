# Databricks APIs Documentation

This directory contains documentation for calling Databricks APIs directly using the Databricks SDK, without wrapper utilities.

## Overview

The Databricks SDK provides direct access to all Databricks APIs. This documentation shows you how to call these APIs directly in your FastAPI application.

## Authentication

All APIs use the same authentication configured in your app:

```python
from databricks.sdk import WorkspaceClient

# Automatically uses your configured authentication
client = WorkspaceClient()
```

## API Categories

### [Databricks SDK](databricks_sdk.md)
- Comprehensive SDK usage patterns
- Authentication and configuration
- Core APIs overview
- FastAPI integration examples

### [Workspace APIs](workspace_apis.md)
- File operations (upload, download, list)
- Directory management
- Notebook operations
- Search and metadata

### [MLflow GenAI](mlflow_genai.md)
- AI agent tracing and observability
- Automated quality evaluation
- Feedback and continuous improvement
- Application lifecycle management

### [Model Serving](model_serving.md)
- List and inspect serving endpoints
- Query serving endpoints
- Batch inference
- Error handling and best practices

## Common Patterns

### Error Handling
```python
from databricks.sdk.errors import DatabricksError

try:
    result = client.workspace.get_status('/path/to/file')
except DatabricksError as e:
    print(f"API Error: {e}")
```

### Pagination
```python
# Most list operations support pagination
for cluster in client.clusters.list():
    print(f"Cluster: {cluster.cluster_name}")
```

### Async Operations
```python
# Many operations are async - wait for completion
cluster_id = client.clusters.create(...)
client.clusters.wait_get_cluster_running(cluster_id)
```

## SDK Documentation

- [Databricks SDK Python Documentation](https://databricks-sdk-py.readthedocs.io/en/latest/)
- [Databricks REST API Reference](https://docs.databricks.com/api/workspace/introduction)
- [SDK Examples](https://github.com/databricks/databricks-sdk-py/tree/main/examples)

## Best Practices

1. **Reuse the client**: Create one `WorkspaceClient` instance per application
2. **Handle errors**: Always wrap API calls in try-catch blocks
3. **Use pagination**: Don't assume all results fit in one response
4. **Check permissions**: Verify user has required permissions for operations
5. **Log API calls**: Add logging for debugging and monitoring