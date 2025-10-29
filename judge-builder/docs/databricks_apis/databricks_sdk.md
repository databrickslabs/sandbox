# Databricks SDK for Python

**Official Documentation**: https://databricks-sdk-py.readthedocs.io/en/latest/

The Databricks SDK for Python provides programmatic access to the Databricks REST APIs, allowing you to manage workspace resources, execute queries, and interact with Databricks services directly from your Python applications.

## Installation

Already included in this template:
```toml
# pyproject.toml
databricks-sdk==0.59.0
```

## Basic Setup

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError

# Initialize client (automatically uses your configured authentication)
client = WorkspaceClient()
```

## Authentication

The SDK automatically uses your app's configured authentication:
- **Personal Access Token (PAT)**: Uses `DATABRICKS_HOST` and `DATABRICKS_TOKEN`
- **CLI Profile**: Uses `DATABRICKS_CONFIG_PROFILE`
- **Service Principal**: When deployed to Databricks Apps

```python
# Authentication is automatic - no additional setup needed
client = WorkspaceClient()

# Verify authentication
try:
    user = client.current_user.me()
    print(f"Authenticated as: {user.user_name}")
except DatabricksError as e:
    print(f"Authentication failed: {e}")
```

## Core APIs

### Workspace Management
```python
# List files and directories
files = client.workspace.list('/Users/user@company.com')

# Upload a file
with open('script.py', 'rb') as f:
    client.workspace.upload('/Users/user@company.com/script.py', f.read())

# Download a file
content = client.workspace.download('/Users/user@company.com/script.py')
```

### Cluster Management
```python
# List clusters
clusters = client.clusters.list()

# Get cluster details
cluster = client.clusters.get('cluster-id')

# Start a cluster
client.clusters.start('cluster-id')

# Create a cluster
cluster_spec = {
  'cluster_name': 'my-cluster',
  'spark_version': '13.3.x-scala2.12',
  'node_type_id': 'i3.xlarge',
  'num_workers': 2
}
cluster_id = client.clusters.create(**cluster_spec).cluster_id
```

### SQL Warehouse Operations
```python
# List SQL warehouses
warehouses = client.warehouses.list()

# Execute SQL query
response = client.statement_execution.execute_statement(
    warehouse_id='warehouse-id',
    statement='SELECT * FROM my_table LIMIT 10'
)

# Get query results
if response.result:
    for row in response.result.data_array:
        print(row)
```

### Jobs and Workflows
```python
# List jobs
jobs = client.jobs.list()

# Run a job
run = client.jobs.run_now(job_id=123)

# Get job run status
run_status = client.jobs.get_run(run.run_id)
```

### Secrets Management
```python
# List secret scopes
scopes = client.secrets.list_scopes()

# Get secret value
secret_value = client.secrets.get_secret('scope-name', 'secret-key')

# Create secret
client.secrets.put_secret('scope-name', 'secret-key', 'secret-value')
```

## Error Handling

```python
from databricks.sdk.errors import (
    NotFound, 
    PermissionDenied, 
    BadRequest,
    DatabricksError
)

try:
    result = client.workspace.get_status('/path/to/file')
except NotFound:
    print("File not found")
except PermissionDenied:
    print("Permission denied")
except BadRequest as e:
    print(f"Bad request: {e}")
except DatabricksError as e:
    print(f"API error: {e}")
```

## Common Patterns

### Pagination
```python
# Most list operations support pagination
for cluster in client.clusters.list():
    print(f"Cluster: {cluster.cluster_name}")
    
# Explicit pagination
clusters = client.clusters.list(limit=10, offset=0)
```

### Async Operations
```python
# Wait for cluster to be ready
cluster_id = client.clusters.create(...).cluster_id
client.clusters.wait_get_cluster_running(cluster_id)

# Wait for job completion
run = client.jobs.run_now(job_id=123)
final_state = client.jobs.wait_get_run_job_terminated_or_skipped(run.run_id)
```

### Batch Operations
```python
# Upload multiple files
import os

def upload_directory(local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            remote_path = f"{remote_dir}/{relative_path}".replace('\\', '/')
            
            with open(local_path, 'rb') as f:
                client.workspace.upload(remote_path, f.read(), overwrite=True)
            print(f"Uploaded: {relative_path}")
```

## FastAPI Integration

### Create API Endpoints
```python
from fastapi import APIRouter, HTTPException
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError

router = APIRouter()
client = WorkspaceClient()

@router.get("/workspace/files")
async def list_workspace_files(path: str = "/"):
  try:
    files = client.workspace.list(path)
    return [{"name": f.path, "type": f.object_type.value} for f in files]
  except DatabricksError as e:
    raise HTTPException(status_code=400, detail=str(e))

@router.post("/clusters/{cluster_id}/start")
async def start_cluster(cluster_id: str):
  try:
    client.clusters.start(cluster_id)
    return {"message": "Cluster start initiated"}
  except DatabricksError as e:
    raise HTTPException(status_code=400, detail=str(e))

@router.post("/sql/execute")
async def execute_sql(warehouse_id: str, query: str):
  try:
    response = client.statement_execution.execute_statement(
      warehouse_id=warehouse_id,
      statement=query
    )
    return {"statement_id": response.statement_id, "status": response.status.state}
  except DatabricksError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

## Advanced Features

### Unity Catalog Integration
```python
# List catalogs
catalogs = client.catalogs.list()

# List schemas
schemas = client.schemas.list('catalog_name')

# List tables
tables = client.tables.list('catalog_name.schema_name')

# Get table info
table = client.tables.get('catalog_name.schema_name.table_name')
```

### Delta Sharing
```python
# List shares
shares = client.shares.list()

# Get share details
share = client.shares.get('share_name')

# List recipients
recipients = client.recipients.list()
```

### Model Serving
```python
# List serving endpoints
endpoints = client.serving_endpoints.list()

# Create serving endpoint
endpoint_spec = {
    'name': 'my-endpoint',
    'config': {
        'served_models': [{
            'model_name': 'my_model',
            'model_version': '1',
            'workload_size': 'Small'
        }]
    }
}
client.serving_endpoints.create(**endpoint_spec)
```

## Configuration

### Environment Variables
```bash
# Set in your .env.local file
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token

# Or use profile
DATABRICKS_CONFIG_PROFILE=your-profile-name
```

### Custom Configuration
```python
from databricks.sdk.config import Config

# Custom configuration
config = Config(
    host='https://your-workspace.cloud.databricks.com',
    token='your-token',
    retry_timeout_seconds=300
)

client = WorkspaceClient(config=config)
```

## Best Practices

1. **Reuse client instances**: Create one `WorkspaceClient` per application
2. **Handle errors gracefully**: Always wrap API calls in try-catch blocks
3. **Use pagination**: Don't assume all results fit in one response
4. **Cache responses**: Cache frequently accessed data to reduce API calls
5. **Monitor rate limits**: Be aware of API rate limits and implement backoff
6. **Use async operations**: Wait for long-running operations to complete
7. **Secure credentials**: Never hardcode tokens in your code

## Resource Links

- **Official Documentation**: https://databricks-sdk-py.readthedocs.io/en/latest/
- **GitHub Repository**: https://github.com/databricks/databricks-sdk-py
- **API Reference**: https://docs.databricks.com/api/workspace/introduction
- **SDK Examples**: https://github.com/databricks/databricks-sdk-py/tree/main/examples
- **Authentication Guide**: https://databricks-sdk-py.readthedocs.io/en/latest/authentication.html