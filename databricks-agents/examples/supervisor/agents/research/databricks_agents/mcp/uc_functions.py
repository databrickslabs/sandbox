"""
Unity Catalog Functions adapter for MCP.

Automatically discovers UC Functions and exposes them as MCP tools.
"""

import logging
from typing import List, Dict, Any, Optional

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class UCFunctionAdapter:
    """
    Adapter for Unity Catalog Functions to MCP protocol.
    
    Discovers UC Functions and converts them to MCP tool format for
    use with agents.
    
    Usage:
        adapter = UCFunctionAdapter(profile="my-profile")
        tools = adapter.discover_functions(catalog="main", schema="functions")
    """
    
    def __init__(self, profile: Optional[str] = None):
        """
        Initialize UC Functions adapter.
        
        Args:
            profile: Databricks CLI profile name
        """
        self.profile = profile
        self._client: Optional[WorkspaceClient] = None
    
    def _get_client(self) -> WorkspaceClient:
        """Get or create workspace client."""
        if self._client is None:
            self._client = (
                WorkspaceClient(profile=self.profile)
                if self.profile
                else WorkspaceClient()
            )
        return self._client
    
    def discover_functions(
        self,
        catalog: str,
        schema: str,
        name_pattern: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover UC Functions and convert to MCP tool format.
        
        Args:
            catalog: UC catalog name
            schema: UC schema name
            name_pattern: Optional name pattern filter (SQL LIKE pattern)
            
        Returns:
            List of tool definitions in MCP format
            
        Example:
            >>> adapter = UCFunctionAdapter()
            >>> tools = adapter.discover_functions("main", "functions")
            >>> for tool in tools:
            ...     print(tool["name"], tool["description"])
        """
        client = self._get_client()
        tools = []
        
        try:
            functions = client.functions.list(
                catalog_name=catalog,
                schema_name=schema,
            )
            
            for func in functions:
                # Skip system functions
                if func.name.startswith("system."):
                    continue
                
                # Apply name pattern filter
                if name_pattern and name_pattern not in func.name:
                    continue
                
                # Convert to MCP tool format
                tool = self._convert_function_to_tool(func)
                if tool:
                    tools.append(tool)
            
            logger.info(
                f"Discovered {len(tools)} UC Functions from {catalog}.{schema}"
            )
            
        except Exception as e:
            logger.error(f"Failed to discover UC Functions: {e}")
        
        return tools
    
    def _convert_function_to_tool(self, func) -> Optional[Dict[str, Any]]:
        """
        Convert a UC Function to MCP tool format.
        
        Args:
            func: Function info from Databricks SDK
            
        Returns:
            MCP tool definition or None if conversion fails
        """
        try:
            # Extract function metadata
            name = func.name.split(".")[-1]  # Get short name
            description = func.comment or f"Unity Catalog function: {name}"
            
            # Build parameter schema
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # Parse function parameters
            if hasattr(func, "input_params") and func.input_params:
                for param in func.input_params.parameters:
                    param_name = param.name
                    param_type = self._map_uc_type_to_json_type(param.type_name)
                    
                    input_schema["properties"][param_name] = {
                        "type": param_type,
                        "description": param.comment or ""
                    }
                    
                    # Parameters without defaults are required
                    if not hasattr(param, "default_value") or param.default_value is None:
                        input_schema["required"].append(param_name)
            
            return {
                "name": name,
                "description": description,
                "inputSchema": input_schema,
                "full_name": func.full_name,
                "source": "unity_catalog"
            }
            
        except Exception as e:
            logger.warning(f"Failed to convert function {func.name}: {e}")
            return None
    
    def _map_uc_type_to_json_type(self, uc_type: str) -> str:
        """
        Map Unity Catalog data type to JSON Schema type.
        
        Args:
            uc_type: UC type name (e.g., "STRING", "BIGINT", "BOOLEAN")
            
        Returns:
            JSON Schema type ("string", "number", "boolean", etc.)
        """
        type_mapping = {
            "STRING": "string",
            "VARCHAR": "string",
            "CHAR": "string",
            "BIGINT": "integer",
            "INT": "integer",
            "INTEGER": "integer",
            "SMALLINT": "integer",
            "TINYINT": "integer",
            "DOUBLE": "number",
            "FLOAT": "number",
            "DECIMAL": "number",
            "BOOLEAN": "boolean",
            "BINARY": "string",
            "DATE": "string",
            "TIMESTAMP": "string",
            "ARRAY": "array",
            "MAP": "object",
            "STRUCT": "object",
        }
        
        uc_type_upper = uc_type.upper()
        return type_mapping.get(uc_type_upper, "string")
    
    async def call_function(
        self,
        full_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a UC Function with given arguments.
        
        Args:
            full_name: Full function name (catalog.schema.function)
            arguments: Function arguments
            
        Returns:
            Function result
            
        Example:
            >>> adapter = UCFunctionAdapter()
            >>> result = await adapter.call_function(
            ...     "main.functions.calculate_tax",
            ...     {"amount": 100, "rate": 0.08}
            ... )
        """
        client = self._get_client()
        
        try:
            # Build SQL query to call the function
            args_list = [f":{key}" for key in arguments.keys()]
            query = f"SELECT {full_name}({', '.join(args_list)})"
            
            # Execute via SQL warehouse
            # Note: This requires a warehouse ID to be configured
            result = client.statement_execution.execute_statement(
                statement=query,
                warehouse_id=self._get_default_warehouse(),
                parameters=[
                    {"name": key, "value": str(value)}
                    for key, value in arguments.items()
                ]
            )
            
            return result.result.data_array[0][0] if result.result.data_array else None
            
        except Exception as e:
            logger.error(f"Failed to call UC Function {full_name}: {e}")
            raise
    
    def _get_default_warehouse(self) -> str:
        """Get default SQL warehouse ID from environment or client."""
        import os
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if not warehouse_id:
            raise ValueError(
                "DATABRICKS_WAREHOUSE_ID not set. "
                "Set this environment variable to use UC Functions."
            )
        return warehouse_id
