# Workspace APIs

Direct usage of Databricks Workspace APIs for file operations, directory management, and notebook handling.

## Setup

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError

# Initialize client (uses your configured authentication)
client = WorkspaceClient()
```

## File Operations

### List Files and Directories

```python
# List files in a directory
try:
  files = client.workspace.list('/Users/user@company.com')
  for file in files:
    print(f"Name: {file.path}")
    print(f"Type: {file.object_type}")  # DIRECTORY, NOTEBOOK, FILE
    print(f"Language: {file.language}")  # PYTHON, SQL, etc.
    print(f"Size: {file.size}")
    print("---")
except DatabricksError as e:
  print(f"Error listing files: {e}")
```

### Get File Information

```python
# Get detailed file information
try:
    file_info = client.workspace.get_status('/path/to/file')
    print(f"Path: {file_info.path}")
    print(f"Object Type: {file_info.object_type}")
    print(f"Language: {file_info.language}")
    print(f"Size: {file_info.size}")
    print(f"Modified: {file_info.modified_at}")
except DatabricksError as e:
    print(f"Error getting file info: {e}")
```

### Upload Files

```python
# Upload a file
try:
    with open('local_file.py', 'rb') as f:
        content = f.read()
    
    client.workspace.upload(
        path='/Users/user@company.com/uploaded_file.py',
        content=content,
        overwrite=True,
        format='SOURCE'  # SOURCE, HTML, JUPYTER, DBC
    )
    print("File uploaded successfully")
except DatabricksError as e:
    print(f"Error uploading file: {e}")
```

### Download Files

```python
# Download a file
try:
    content = client.workspace.download(
        path='/Users/user@company.com/file.py',
        format='SOURCE'
    )
    
    with open('downloaded_file.py', 'wb') as f:
        f.write(content)
    print("File downloaded successfully")
except DatabricksError as e:
    print(f"Error downloading file: {e}")
```

### Export Files

```python
# Export a notebook
try:
    content = client.workspace.export(
        path='/Users/user@company.com/notebook',
        format='JUPYTER'  # SOURCE, HTML, JUPYTER, DBC
    )
    
    with open('exported_notebook.ipynb', 'wb') as f:
        f.write(content)
    print("Notebook exported successfully")
except DatabricksError as e:
    print(f"Error exporting notebook: {e}")
```

## Directory Operations

### Create Directory

```python
# Create a directory
try:
    client.workspace.mkdirs('/Users/user@company.com/new_directory')
    print("Directory created successfully")
except DatabricksError as e:
    print(f"Error creating directory: {e}")
```

### Delete Files/Directories

```python
# Delete a file or directory
try:
    client.workspace.delete(
        path='/Users/user@company.com/file_to_delete.py',
        recursive=True  # Required for directories
    )
    print("File/directory deleted successfully")
except DatabricksError as e:
    print(f"Error deleting: {e}")
```

## Search Operations

### Search Files

```python
# Search for files by name pattern
try:
    # Note: This is a basic example - actual search depends on your workspace setup
    all_files = []
    
    def search_directory(path):
        try:
            files = client.workspace.list(path)
            for file in files:
                if file.object_type.value == 'DIRECTORY':
                    search_directory(file.path)
                elif 'search_term' in file.path.lower():
                    all_files.append(file)
        except DatabricksError:
            pass  # Skip directories we can't access
    
    search_directory('/Users')
    
    for file in all_files:
        print(f"Found: {file.path}")
        
except DatabricksError as e:
    print(f"Error searching: {e}")
```

## Batch Operations

### Upload Multiple Files

```python
import os

def upload_directory(local_dir, remote_dir):
    """Upload all files from local directory to remote directory"""
    try:
        # Create remote directory
        client.workspace.mkdirs(remote_dir)
        
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_dir)
                remote_path = f"{remote_dir}/{relative_path}".replace('\\', '/')
                
                with open(local_path, 'rb') as f:
                    content = f.read()
                
                client.workspace.upload(
                    path=remote_path,
                    content=content,
                    overwrite=True,
                    format='SOURCE'
                )
                print(f"Uploaded: {local_path} -> {remote_path}")
                
    except DatabricksError as e:
        print(f"Error uploading directory: {e}")

# Usage
upload_directory('./local_project', '/Users/user@company.com/remote_project')
```

## Error Handling Patterns

```python
from databricks.sdk.errors import NotFound, PermissionDenied, BadRequest

def safe_file_operation(path):
    try:
        return client.workspace.get_status(path)
    except NotFound:
        print(f"File not found: {path}")
        return None
    except PermissionDenied:
        print(f"Permission denied: {path}")
        return None
    except BadRequest as e:
        print(f"Bad request: {e}")
        return None
    except DatabricksError as e:
        print(f"Unexpected error: {e}")
        return None
```

## Common Use Cases

### Sync Local Project to Workspace

```python
def sync_project_to_workspace(local_dir, workspace_dir):
    """Sync local project directory to Databricks workspace"""
    try:
        # Create workspace directory
        client.workspace.mkdirs(workspace_dir)
        
        # Upload all Python files
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                if file.endswith('.py'):
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, local_dir)
                    remote_path = f"{workspace_dir}/{relative_path}".replace('\\', '/')
                    
                    with open(local_path, 'rb') as f:
                        content = f.read()
                    
                    client.workspace.upload(
                        path=remote_path,
                        content=content,
                        overwrite=True,
                        format='SOURCE'
                    )
                    print(f"Synced: {relative_path}")
                    
    except DatabricksError as e:
        print(f"Error syncing project: {e}")
```

### Backup Workspace Directory

```python
def backup_workspace_directory(workspace_dir, local_backup_dir):
    """Backup workspace directory to local filesystem"""
    import os
    
    try:
        os.makedirs(local_backup_dir, exist_ok=True)
        
        def backup_recursive(remote_path, local_path):
            files = client.workspace.list(remote_path)
            for file in files:
                if file.object_type.value == 'DIRECTORY':
                    new_local_path = os.path.join(local_path, os.path.basename(file.path))
                    os.makedirs(new_local_path, exist_ok=True)
                    backup_recursive(file.path, new_local_path)
                else:
                    content = client.workspace.download(file.path, format='SOURCE')
                    filename = os.path.basename(file.path)
                    if file.language:
                        filename += f".{file.language.value.lower()}"
                    
                    with open(os.path.join(local_path, filename), 'wb') as f:
                        f.write(content)
                    print(f"Backed up: {file.path}")
        
        backup_recursive(workspace_dir, local_backup_dir)
        
    except DatabricksError as e:
        print(f"Error backing up: {e}")
```

## API Reference

- [Workspace API Documentation](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/workspace.html)
- [REST API Reference](https://docs.databricks.com/api/workspace/workspace)
- [File Formats](https://docs.databricks.com/api/workspace/workspace/export#format)