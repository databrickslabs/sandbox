"""
Code generation service for supervisors.

This service generates code-first supervisors from collections using
Jinja2 templates. Generated supervisors use Pattern 3 (dynamic tool
discovery at runtime).
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.db_adapter import WarehouseDB  # Auto-switches between SQLite and Warehouse
from app.config import settings


class GeneratorError(Exception):
    """Raised when code generation fails."""
    pass


class GeneratorService:
    """Service for generating supervisor code from collections."""

    def __init__(self):
        """Initialize generator with Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # Don't escape Python code
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def fetch_collection_items(
        self, collection_id: int
    ) -> tuple[Dict, List[Dict]]:
        """
        Fetch collection and its items with full details.

        Args:
            collection_id: Collection ID

        Returns:
            Tuple of (collection, items_list)
            items_list contains dicts with type, name, description, server_url

        Raises:
            GeneratorError: If collection not found or has no items
        """
        collection = WarehouseDB.get_collection(collection_id)
        if not collection:
            raise GeneratorError(f"Collection with id {collection_id} not found")

        items_data = []

        # Get all collection items with joined data
        items = WarehouseDB.list_collection_items(collection_id)

        if not items:
            # Allow empty collections - they can still generate supervisors
            # with no tools initially
            pass

        # Process each item
        for item in items:
            if item.get('tool_id'):
                # Individual tool
                tool = WarehouseDB.get_tool(item['tool_id'])
                if tool:
                    mcp_server = WarehouseDB.get_mcp_server(tool.get('mcp_server_id')) if tool.get('mcp_server_id') else None
                    items_data.append({
                        "type": "tool",
                        "name": tool.get('name', ''),
                        "description": tool.get('description') or "",
                        "server_url": mcp_server.get('server_url', '') if mcp_server else "",
                    })

            elif item.get('mcp_server_id'):
                # Entire MCP server (all its tools)
                mcp_server = WarehouseDB.get_mcp_server(item['mcp_server_id'])
                if mcp_server:
                    items_data.append({
                        "type": "mcp_server",
                        "name": "MCP Server",
                        "description": f"All tools from {mcp_server.get('server_url', '')}",
                        "server_url": mcp_server.get('server_url', ''),
                    })

            elif item.get('app_id'):
                # Databricks App (all its MCP servers)
                app = WarehouseDB.get_app(item['app_id'])
                if app:
                    # For now, just add the app as an item
                    # TODO: Get MCP servers for this app
                    items_data.append({
                        "type": "app",
                        "name": app.get('name', ''),
                        "description": f"Tools from {app.get('name', '')}",
                        "server_url": app.get('url', ''),
                    })

        return collection, items_data

    def resolve_mcp_server_urls(self, items: List[Dict]) -> List[str]:
        """
        Extract unique MCP server URLs from collection items.

        Args:
            items: List of item dictionaries from fetch_collection_items

        Returns:
            List of unique MCP server URLs
        """
        urls = set()
        for item in items:
            server_url = item.get("server_url", "").strip()
            if server_url:
                urls.add(server_url)
        return sorted(list(urls))

    def generate_supervisor_code(
        self,
        collection_id: int,
        llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
        app_name: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate supervisor code from a collection.

        Creates three files:
        - supervisor.py: Main supervisor code with Pattern 3
        - requirements.txt: Python dependencies
        - app.yaml: Databricks Apps deployment config

        Args:
            collection_id: Collection ID
            llm_endpoint: Databricks Foundation Model endpoint name
            app_name: Optional custom app name (defaults to collection name)

        Returns:
            Dictionary mapping filenames to file contents:
            {
                "supervisor.py": "...",
                "requirements.txt": "...",
                "app.yaml": "..."
            }

        Raises:
            GeneratorError: If generation fails
        """
        # Fetch collection data
        collection, items = self.fetch_collection_items(collection_id)

        # Extract MCP server URLs
        mcp_server_urls = self.resolve_mcp_server_urls(items)

        # Generate app name
        if not app_name:
            # Convert collection name to valid app name
            # e.g., "Expert Research Toolkit" -> "expert-research-toolkit"
            collection_name = collection.get('name', 'supervisor')
            app_name = collection_name.lower().replace(" ", "-")
            app_name = "".join(c for c in app_name if c.isalnum() or c == "-")

        # Template context
        context = {
            "collection_id": collection_id,
            "collection_name": collection.get('name', ''),
            "collection_description": collection.get('description') or "",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "tool_list": items,
            "mcp_server_urls": ",".join(mcp_server_urls),
            "llm_endpoint": llm_endpoint,
            "app_name": app_name,
            "databricks_host": settings.databricks_host or "${DATABRICKS_HOST}",
        }

        # Generate files
        files = {}

        try:
            # Generate supervisor.py
            template = self.env.get_template("supervisor_code_first.py.jinja2")
            files["supervisor.py"] = template.render(**context)

            # Generate requirements.txt
            template = self.env.get_template("requirements.txt.jinja2")
            files["requirements.txt"] = template.render(**context)

            # Generate app.yaml
            template = self.env.get_template("app.yaml.jinja2")
            files["app.yaml"] = template.render(**context)

        except TemplateNotFound as e:
            raise GeneratorError(f"Template not found: {e.name}")
        except Exception as e:
            raise GeneratorError(f"Template rendering failed: {str(e)}")

        return files

    def validate_python_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate that generated Python code is syntactically correct.

        Args:
            code: Python source code

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, error_msg) if invalid
        """
        try:
            compile(code, "<generated>", "exec")
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def generate_and_validate(
        self,
        collection_id: int,
        llm_endpoint: str = "databricks-meta-llama-3-1-70b-instruct",
        app_name: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate supervisor code and validate Python syntax.

        This is a convenience method that combines generation and validation.

        Args:
            collection_id: Collection ID
            llm_endpoint: Databricks Foundation Model endpoint name
            app_name: Optional custom app name

        Returns:
            Dictionary of generated files

        Raises:
            GeneratorError: If generation or validation fails
        """
        files = self.generate_supervisor_code(
            collection_id=collection_id,
            llm_endpoint=llm_endpoint,
            app_name=app_name,
        )

        # Validate supervisor.py
        is_valid, error_msg = self.validate_python_syntax(files["supervisor.py"])
        if not is_valid:
            raise GeneratorError(f"Generated Python code is invalid: {error_msg}")

        return files


# Singleton instance
_generator_service: Optional[GeneratorService] = None


def get_generator_service() -> GeneratorService:
    """
    Get or create singleton generator service instance.

    Returns:
        GeneratorService instance
    """
    global _generator_service
    if _generator_service is None:
        _generator_service = GeneratorService()
    return _generator_service
