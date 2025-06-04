# Databricks notebook source
# MAGIC %md
# MAGIC # Convert Python Notebooks to SQL Notebooks (Experimental)
# MAGIC This notebook facilitates the conversion of Databricks Python notebooks into SQL notebooks, allowing for the transformation of Python-based data workflows to SQL-based implementations.
# MAGIC
# MAGIC ## Task Overview
# MAGIC The following tasks are accomplished in this notebook:
# MAGIC
# MAGIC 1. **Scan Python Notebooks**: Recursively scan the specified directory for Databricks Python notebooks (.py files).
# MAGIC 2. **Batch Conversion**: Use LLM-powered batch inference to convert Python code containing `spark.sql()` calls and `dbutils.widgets.get()` to equivalent SQL statements.
# MAGIC 3. **Export SQL Notebooks**: Create and export the converted SQL notebooks to the specified output directory in the workspace.
# MAGIC 4. **Error Handling**: Process conversion results and handle any errors that occur during the conversion or export process.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install and import libraries

# COMMAND ----------

# DBTITLE 1,Install Packages
# MAGIC %pip install -r requirements.txt
# MAGIC %pip install databricks-sdk --upgrade
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json
import os
import base64
from typing import List, Dict, Any, Tuple
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace
from pyscripts.batch_inference_helper import (AsyncChatClient,
                                              BatchInferenceManager,
                                              BatchInferenceRequest)
from pyscripts.conversion_prompt_helper import ConversionPromptHelper

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
# Required Parameters
dbutils.widgets.text("python_input_dir", "", "Python Notebooks Directory (Required)")
dbutils.widgets.text("sql_output_dir", "", "SQL Notebooks Output Directory (Required)")

# Required Parameters with Default Values
dbutils.widgets.text("endpoint_name", "databricks-claude-3-7-sonnet", "Serving Endpoint Name (Required)")
dbutils.widgets.text("concurrency", "4", "Concurrency Requests")
dbutils.widgets.dropdown("log_level", "INFO", ["DEBUG", "INFO"], "Log Level")
dbutils.widgets.dropdown("comment_lang", "English", [
                         "Chinese", "English", "French", "German", "Italian", "Japanese", "Korean", "Portuguese", "Spanish"], "Comment Language")

# Optional Parameters
dbutils.widgets.text("request_params", "", "Chat Request Params")
dbutils.widgets.text("logging_interval", "1", "Logging Interval")
dbutils.widgets.text("timeout", "300", "Timeout Seconds")
dbutils.widgets.text("max_retries_backpressure", "10", "Max Retries on Backpressure")
dbutils.widgets.text("max_retries_other", "3", "Max Retries on Other Errors")

# COMMAND ----------

# DBTITLE 1,Load Configurations
python_input_dir = dbutils.widgets.get("python_input_dir")
sql_output_dir = dbutils.widgets.get("sql_output_dir")
endpoint_name = dbutils.widgets.get("endpoint_name")
concurrency = int(dbutils.widgets.get("concurrency"))
log_level = dbutils.widgets.get("log_level")
comment_lang = dbutils.widgets.get("comment_lang")
request_params = dbutils.widgets.get("request_params")
logging_interval = int(dbutils.widgets.get("logging_interval"))
timeout = int(dbutils.widgets.get("timeout"))
max_retries_backpressure = int(dbutils.widgets.get("max_retries_backpressure"))
max_retries_other = int(dbutils.widgets.get("max_retries_other"))

# Use the databricks_python_notebook_to_databricks_sql_notebook.yml prompt
conversion_prompt_yaml = "pyscripts/conversion_prompt_yaml/databricks_python_notebook_to_databricks_sql_notebook.yml"

print(f"Python input directory: {python_input_dir}")
print(f"SQL output directory: {sql_output_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parameters
# MAGIC
# MAGIC Parameter Name | Required | Description | Default Value
# MAGIC --- | --- | --- | ---
# MAGIC `python_input_dir` | Yes | The directory containing Python notebooks to convert. |
# MAGIC `sql_output_dir` | Yes | The directory where converted SQL notebooks will be saved. |
# MAGIC `endpoint_name` | Yes | The name of the Databricks Model Serving endpoint for LLM conversion. | `databricks-claude-3-7-sonnet`
# MAGIC `concurrency` | Yes | The number of concurrent requests sent to the model serving endpoint. | `4`
# MAGIC `log_level` | Yes | The logging level to use for the batch inference process. Options are `INFO` for standard logging or `DEBUG` for detailed debug information. | `INFO`
# MAGIC `comment_lang` | Yes | The language for comments to be added to the converted SQL notebooks. | `English`
# MAGIC `request_params` | No | The extra chat request parameters in JSON format. Empty value will use model's default parameters. |
# MAGIC `logging_interval` | Yes | The number of requests processed before logging a progress update. | `1`
# MAGIC `timeout` | Yes | The timeout for an HTTP request on the client side, in seconds. | `300`
# MAGIC `max_retries_backpressure` | Yes | The maximum number of retries on backpressure status code (such as `429` or `503`). | `10`
# MAGIC `max_retries_other` | Yes | The maximum number of retries on other errors (such as `5xx`, `408`, or `409`). | `3`

# COMMAND ----------

# DBTITLE 1,Helper Functions for File Operations
def is_databricks_notebook(content: str) -> bool:
    """Check if the content is from a Databricks notebook."""
    # Check for Databricks notebook source marker in first few lines
    first_lines = content[:500]  # Check more content
    return ("# Databricks notebook source" in first_lines or 
            "# MAGIC" in first_lines or
            "# COMMAND ----------" in first_lines)

def get_relative_path(file_path: str, base_dir: str) -> str:
    """Get relative path from base directory."""
    # Normalize paths
    file_path = file_path.rstrip('/')
    base_dir = base_dir.rstrip('/')
    
    if file_path.startswith(base_dir):
        relative = file_path[len(base_dir):].lstrip('/')
        return relative
    return file_path

def read_notebook_content(file_path: str) -> Tuple[str, int]:
    """
    Read the content of a Databricks notebook file.
    Returns tuple of (content, size_in_bytes)
    """
    try:
        w = WorkspaceClient()
        export_response = w.workspace.export(file_path, format=workspace.ExportFormat.SOURCE)
        
        # Handle both old and new SDK versions
        if hasattr(export_response, 'content'):
            content_data = export_response.content
        else:
            content_data = export_response
        
        # Handle both string and bytes
        if isinstance(content_data, str):
            # Check if it's base64 encoded
            try:
                # Try to decode as base64
                decoded_bytes = base64.b64decode(content_data)
                content = decoded_bytes.decode('utf-8')
                size_bytes = len(decoded_bytes)
            except Exception:
                # If base64 decoding fails, treat as plain text
                content = content_data
                size_bytes = len(content_data.encode('utf-8'))
        else:
            content = content_data.decode('utf-8')
            size_bytes = len(content_data)
            
        return content, size_bytes
    except Exception as e:
        print(f"Error reading notebook {file_path}: {e}")
        return None, 0

def list_python_notebooks(directory: str) -> List[Dict[str, Any]]:
    """
    Recursively list all Python notebook files in a directory.
    Returns a list of dictionaries with file information.
    """
    notebooks = []
    w = WorkspaceClient()
    
    try:
        # List all files in the directory
        items = w.workspace.list(directory, recursive=True)
        
        for item in items:
            if item.object_type == workspace.ObjectType.NOTEBOOK and item.language == workspace.Language.PYTHON:
                notebooks.append({
                    "path": item.path,
                    "name": item.path.split("/")[-1],
                    "size": item.size if hasattr(item, 'size') else 0
                })
                    
    except Exception as e:
        print(f"Error listing notebooks in {directory}: {e}")
        
    return notebooks

# COMMAND ----------

# MAGIC %md
# MAGIC ## Scan for Python notebooks
# MAGIC The following scans the input directory for Python notebooks and prepares them for conversion.

# COMMAND ----------

# DBTITLE 1,Scan Directory for Python Notebooks
# Find all Python notebooks in the input directory
print(f"Scanning {python_input_dir} for Python notebooks (.py files)...")
python_notebooks = list_python_notebooks(python_input_dir)

print(f"Found {len(python_notebooks)} Python notebooks")

# Read notebook contents and filter by size
conversion_data = []
skipped_files = []

for notebook in python_notebooks:
    content, size_bytes = read_notebook_content(notebook["path"])
    size_mb = size_bytes / (1024 * 1024)
    
    if content is None:
        skipped_files.append((notebook["path"], "Could not read file"))
        continue
        
    if not is_databricks_notebook(content):
        skipped_files.append((notebook["path"], "Not a Databricks notebook"))
        continue
    
    conversion_data.append({
        'python_notebook_path': notebook["path"],
        'python_content': content,
        'size_mb': size_mb,
        'relative_path': get_relative_path(notebook["path"], python_input_dir)
    })

print(f"\nFiles to convert: {len(conversion_data)}")
print(f"Files skipped: {len(skipped_files)}")

if skipped_files:
    print("\nSkipped files:")
    for path, reason in skipped_files[:10]:  # Show first 10
        print(f"  - {path}: {reason}")
    if len(skipped_files) > 10:
        print(f"  ... and {len(skipped_files) - 10} more")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert Python notebooks to SQL
# MAGIC The following converts the Python notebooks to SQL using batch inference.

# COMMAND ----------

# DBTITLE 1,Prepare Conversion Requests
if not conversion_data:
    print("No files to convert. Exiting.")
    dbutils.notebook.exit(json.dumps([]))

# Load conversion prompt
helper = ConversionPromptHelper(conversion_prompt_yaml, comment_lang)
system_message = helper.get_system_message()
few_shots = helper.get_few_shots()

# Prepare conversion requests
conversion_requests = []
for i, data in enumerate(conversion_data):
    request = BatchInferenceRequest(
        index=i,
        text=data['python_content'],
        system_message=system_message,
        few_shots=few_shots
    )
    # Store metadata for later use
    request.metadata = {
        "python_notebook_path": data['python_notebook_path'],
        "relative_path": data['relative_path'],
        "size_mb": data['size_mb']
    }
    conversion_requests.append(request)

print(f"Prepared {len(conversion_requests)} conversion requests")


# COMMAND ----------

# DBTITLE 1,Execute Batch Conversion
# Create batch manager
manager = BatchInferenceManager(
    client=AsyncChatClient(
        endpoint_name=endpoint_name,
        request_params=request_params,
        timeout=timeout,
        max_retries_backpressure=max_retries_backpressure,
        max_retries_other=max_retries_other,
        log_level=log_level,
    ),
    concurrency=concurrency,
    logging_interval=logging_interval,
    log_level=log_level,
)

# Execute batch conversion
print(f"\nStarting Python to SQL notebook conversion...")
print(f"Using endpoint: {endpoint_name}")
print(f"Concurrency: {concurrency}")
print("-" * 50)

conversion_results = await manager.batch_inference(conversion_requests)
print(f"\nConversion completed. {len(conversion_results)} results received.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process conversion results
# MAGIC The following processes the conversion results and prepares SQL notebook content.

# COMMAND ----------

# DBTITLE 1,Process Results and Prepare SQL Notebooks
sql_notebooks = []
conversion_errors = []

for i, result in enumerate(conversion_results):
    try:
        # Get metadata from the original request
        metadata = conversion_requests[i].metadata
        
        # Check if result has content (success case)
        if hasattr(result, 'content') and result.content:
            sql_notebooks.append({
                "python_notebook_path": metadata["python_notebook_path"],
                "relative_path": metadata["relative_path"],
                "sql_content": result.content,
                "size_mb": metadata["size_mb"]
            })
        elif hasattr(result, 'error') and result.error:
            # Error case
            conversion_errors.append({
                "python_notebook_path": metadata["python_notebook_path"],
                "error": str(result.error)
            })
        else:
            # Unknown case
            conversion_errors.append({
                "python_notebook_path": metadata["python_notebook_path"],
                "error": f"Unknown result format: {result}"
            })
    except Exception as e:
        print(f"Error processing result {i}: {e}")
        if i < len(conversion_requests):
            metadata = conversion_requests[i].metadata
            conversion_errors.append({
                "python_notebook_path": metadata.get("python_notebook_path", "unknown"),
                "error": str(e)
            })
        else:
            conversion_errors.append({
                "python_notebook_path": "unknown",
                "error": str(e)
            })

print(f"\nSuccessfully converted {len(sql_notebooks)} notebooks to SQL")
if conversion_errors:
    print(f"Encountered {len(conversion_errors)} conversion errors")
    for error in conversion_errors[:3]:  # Show first 3 errors
        print(f"  - {error['python_notebook_path']}: {error['error']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export SQL notebooks
# MAGIC The following exports the converted SQL notebooks to the workspace.

# COMMAND ----------

# DBTITLE 1,Export SQL Notebooks
if sql_notebooks:
    export_results = []
    
    for notebook in sql_notebooks:
        try:
            # Determine output path for SQL notebook
            relative_path = notebook["relative_path"]
            
            # Change extension from .py to .sql
            if relative_path.endswith('.py'):
                sql_relative_path = relative_path[:-3] + '.sql'
            else:
                sql_relative_path = relative_path + '.sql'
            
            sql_output_path = os.path.join(sql_output_dir, sql_relative_path).replace('\\', '/')
            
            # Export notebook directly using WorkspaceClient
            w = WorkspaceClient()
            
            # Ensure directory exists by creating parent path
            parent_path = "/".join(sql_output_path.split("/")[:-1])
            try:
                w.workspace.mkdirs(parent_path)
            except Exception:
                pass  # Directory might already exist
            
            # Encode content as base64
            encoded_content = base64.b64encode(notebook["sql_content"].encode('utf-8')).decode('utf-8')
            
            # Export as SQL notebook
            w.workspace.import_(
                content=encoded_content,
                path=sql_output_path,
                format=workspace.ImportFormat.SOURCE,
                language=workspace.Language.SQL,
                overwrite=True
            )
            
            result_success = True
            result_error = None
            
            export_results.append({
                "python_notebook_path": notebook["python_notebook_path"],
                "sql_output_path": sql_output_path,
                "success": result_success,
                "error": result_error,
                "size_mb": notebook["size_mb"]
            })
            
        except Exception as e:
            export_results.append({
                "python_notebook_path": notebook["python_notebook_path"],
                "sql_output_path": "failed",
                "success": False,
                "error": str(e),
                "size_mb": notebook.get("size_mb", 0)
            })
    
    # Display results
    successful_exports = [r for r in export_results if r["success"]]
    failed_exports = [r for r in export_results if not r["success"]]
    
    print(f"\nSuccessfully exported {len(successful_exports)} SQL notebooks")
    if failed_exports:
        print(f"Failed to export {len(failed_exports)} SQL notebooks")
else:
    print("No SQL notebooks to export")
    export_results = []

# COMMAND ----------

# Return results as JSON
if 'export_results' in locals():
    dbutils.notebook.exit(json.dumps(export_results))
else:
    dbutils.notebook.exit(json.dumps([]))
