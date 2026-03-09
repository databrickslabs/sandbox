"""
Tests for code generation service.

Tests the GeneratorService for creating code-first supervisors
from collections using Pattern 3 (dynamic tool discovery).
"""

import pytest
from sqlalchemy.orm import Session

from app.services.generator import GeneratorService, GeneratorError, get_generator_service
from app.models import Collection, CollectionItem, App, MCPServer, Tool, MCPServerKind


class TestGeneratorService:
    """Test suite for GeneratorService."""

    def test_singleton_instance(self):
        """Test that get_generator_service returns singleton."""
        service1 = get_generator_service()
        service2 = get_generator_service()
        assert service1 is service2

    def test_fetch_collection_items_not_found(self, db: Session):
        """Test fetch_collection_items with non-existent collection."""
        service = GeneratorService()

        with pytest.raises(GeneratorError, match="Collection with id 999 not found"):
            service.fetch_collection_items(999)

    def test_fetch_collection_items_empty(self, db: Session):
        """Test fetch_collection_items with empty collection."""
        # Create empty collection
        collection = Collection(name="Empty Collection", description="No items")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        result_collection, items = service.fetch_collection_items(
            collection.id
        )

        assert result_collection['id'] == collection.id
        assert len(items) == 0

    def test_fetch_collection_items_with_tools(self, db: Session):
        """Test fetch_collection_items with individual tools."""
        # Create collection with tools
        collection = Collection(name="Test Collection", description="Test")
        db.add(collection)
        db.commit()

        # Create MCP server
        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        # Create tools
        tool1 = Tool(
            mcp_server_id=mcp_server.id,
            name="search_tool",
            description="Search for things",
            parameters='{"type": "object"}',
        )
        tool2 = Tool(
            mcp_server_id=mcp_server.id,
            name="analysis_tool",
            description="Analyze data",
            parameters='{"type": "object"}',
        )
        db.add_all([tool1, tool2])
        db.commit()

        # Add tools to collection
        item1 = CollectionItem(collection_id=collection.id, tool_id=tool1.id)
        item2 = CollectionItem(collection_id=collection.id, tool_id=tool2.id)
        db.add_all([item1, item2])
        db.commit()

        service = GeneratorService()
        result_collection, items = service.fetch_collection_items(
            collection.id
        )

        assert result_collection['id'] == collection.id
        assert len(items) == 2
        assert items[0]["type"] == "tool"
        assert items[0]["name"] == "search_tool"
        assert items[0]["server_url"] == "https://mcp.example.com"
        assert items[1]["name"] == "analysis_tool"

    def test_fetch_collection_items_with_mcp_server(self, db: Session):
        """Test fetch_collection_items with entire MCP server."""
        # Create collection
        collection = Collection(name="Server Collection", description="Test")
        db.add(collection)
        db.commit()

        # Create MCP server
        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.MANAGED,
        )
        db.add(mcp_server)
        db.commit()

        # Add server to collection
        item = CollectionItem(collection_id=collection.id, mcp_server_id=mcp_server.id)
        db.add(item)
        db.commit()

        service = GeneratorService()
        result_collection, items = service.fetch_collection_items(
            collection.id
        )

        assert len(items) == 1
        assert items[0]["type"] == "mcp_server"
        assert items[0]["server_url"] == "https://mcp.example.com"

    def test_fetch_collection_items_with_app(self, db: Session):
        """Test fetch_collection_items with Databricks App."""
        # Create collection
        collection = Collection(name="App Collection", description="Test")
        db.add(collection)
        db.commit()

        # Create app
        app = App(name="test-app", owner="user@example.com", url="https://app.example.com")
        db.add(app)
        db.commit()

        # Create MCP servers for app
        server1 = MCPServer(
            app_id=app.id,
            server_url="https://mcp1.example.com",
            kind=MCPServerKind.MANAGED,
        )
        server2 = MCPServer(
            app_id=app.id,
            server_url="https://mcp2.example.com",
            kind=MCPServerKind.MANAGED,
        )
        db.add_all([server1, server2])
        db.commit()

        # Add app to collection
        item = CollectionItem(collection_id=collection.id, app_id=app.id)
        db.add(item)
        db.commit()

        service = GeneratorService()
        result_collection, items = service.fetch_collection_items(
            collection.id
        )

        assert len(items) == 1  # App appears as single item
        assert items[0]["type"] == "app"
        assert items[0]["name"] == "test-app"

    def test_resolve_mcp_server_urls_empty(self):
        """Test resolve_mcp_server_urls with empty items."""
        service = GeneratorService()
        urls = service.resolve_mcp_server_urls([])
        assert urls == []

    def test_resolve_mcp_server_urls_unique(self):
        """Test resolve_mcp_server_urls removes duplicates."""
        service = GeneratorService()
        items = [
            {"server_url": "https://mcp1.example.com"},
            {"server_url": "https://mcp2.example.com"},
            {"server_url": "https://mcp1.example.com"},  # Duplicate
            {"server_url": ""},  # Empty
        ]
        urls = service.resolve_mcp_server_urls(items)

        assert len(urls) == 2
        assert "https://mcp1.example.com" in urls
        assert "https://mcp2.example.com" in urls
        assert urls == sorted(urls)  # Should be sorted

    def test_generate_supervisor_code_empty_collection(self, db: Session):
        """Test generate_supervisor_code with empty collection."""
        # Create empty collection
        collection = Collection(name="Empty Collection", description="No tools")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        assert "supervisor.py" in files
        assert "requirements.txt" in files
        assert "app.yaml" in files

        # Verify supervisor.py contains expected content
        supervisor_code = files["supervisor.py"]
        assert "Empty Collection" in supervisor_code
        assert "Pattern 3" in supervisor_code
        assert "fetch_tool_infos" in supervisor_code
        assert "run_supervisor" in supervisor_code

    def test_generate_supervisor_code_with_one_tool(self, db: Session):
        """Test generate_supervisor_code with single tool."""
        # Create collection with one tool
        collection = Collection(name="Single Tool", description="Test")
        db.add(collection)
        db.commit()

        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        tool = Tool(
            mcp_server_id=mcp_server.id,
            name="test_tool",
            description="Test tool",
            parameters='{"type": "object"}',
        )
        db.add(tool)
        db.commit()

        item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
        db.add(item)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        # Verify MCP server URL is included
        supervisor_code = files["supervisor.py"]
        assert "https://mcp.example.com" in supervisor_code or "MCP_SERVER_URLS" in supervisor_code

        # Verify app.yaml includes MCP server URL
        app_yaml = files["app.yaml"]
        assert "https://mcp.example.com" in app_yaml

    def test_generate_supervisor_code_with_many_tools(self, db: Session):
        """Test generate_supervisor_code with 10+ tools."""
        # Create collection
        collection = Collection(name="Many Tools", description="Lots of tools")
        db.add(collection)
        db.commit()

        # Create multiple MCP servers
        servers = []
        for i in range(3):
            server = MCPServer(
                server_url=f"https://mcp{i}.example.com",
                kind=MCPServerKind.CUSTOM,
            )
            db.add(server)
            servers.append(server)
        db.commit()

        # Create 12 tools across servers
        for i in range(12):
            server = servers[i % 3]
            tool = Tool(
                mcp_server_id=server.id,
                name=f"tool_{i}",
                description=f"Tool number {i}",
                parameters='{"type": "object"}',
            )
            db.add(tool)
            db.commit()

            item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
            db.add(item)

        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        # Verify all server URLs are included
        app_yaml = files["app.yaml"]
        assert "mcp0.example.com" in app_yaml
        assert "mcp1.example.com" in app_yaml
        assert "mcp2.example.com" in app_yaml

    def test_generate_supervisor_code_custom_llm_endpoint(self, db: Session):
        """Test generate_supervisor_code with custom LLM endpoint."""
        # Create collection
        collection = Collection(name="Custom LLM", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(
            collection.id,
            llm_endpoint="databricks-dbrx-instruct",
        )

        # Verify custom LLM endpoint
        app_yaml = files["app.yaml"]
        assert "databricks-dbrx-instruct" in app_yaml

    def test_generate_supervisor_code_custom_app_name(self, db: Session):
        """Test generate_supervisor_code with custom app name."""
        # Create collection
        collection = Collection(name="Test Collection", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(
            collection.id,
            app_name="my-custom-supervisor",
        )

        # Verify custom app name
        app_yaml = files["app.yaml"]
        assert "my-custom-supervisor" in app_yaml

    def test_generate_supervisor_code_app_name_normalization(self, db: Session):
        """Test that collection name is normalized to valid app name."""
        # Create collection with special characters
        collection = Collection(
            name="Expert Research Toolkit!!",
            description="Special chars",
        )
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        # Verify app name is normalized (in the name: field, not in comments/descriptions)
        app_yaml = files["app.yaml"]
        assert "name: expert-research-toolkit" in app_yaml
        # Original name may appear in comments/descriptions, but normalized name should be in the name field

    def test_validate_python_syntax_valid(self):
        """Test validate_python_syntax with valid code."""
        service = GeneratorService()
        code = """
def hello():
    return "world"

x = 42
        """
        is_valid, error = service.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_validate_python_syntax_invalid(self):
        """Test validate_python_syntax with invalid code."""
        service = GeneratorService()
        code = """
def hello():
    return "world"
    invalid syntax here!!!
        """
        is_valid, error = service.validate_python_syntax(code)
        assert is_valid is False
        assert error is not None
        assert "Syntax error" in error or "Validation error" in error

    def test_generate_and_validate_success(self, db: Session):
        """Test generate_and_validate with valid generation."""
        # Create collection
        collection = Collection(name="Valid Collection", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_and_validate(collection.id)

        assert "supervisor.py" in files
        assert "requirements.txt" in files
        assert "app.yaml" in files

        # Should not raise error
        assert len(files["supervisor.py"]) > 0

    def test_generated_code_is_valid_python(self, db: Session):
        """Test that generated supervisor code is syntactically valid Python."""
        # Create collection with tools
        collection = Collection(name="Syntax Test", description="Test")
        db.add(collection)
        db.commit()

        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        tool = Tool(
            mcp_server_id=mcp_server.id,
            name="test_tool",
            description="Test",
            parameters='{"type": "object"}',
        )
        db.add(tool)
        db.commit()

        item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
        db.add(item)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        # Validate generated code
        is_valid, error = service.validate_python_syntax(files["supervisor.py"])
        assert is_valid is True, f"Generated code has syntax error: {error}"

    def test_generated_code_contains_pattern3_elements(self, db: Session):
        """Test that generated code includes Pattern 3 elements."""
        # Create collection
        collection = Collection(name="Pattern 3 Test", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        supervisor_code = files["supervisor.py"]

        # Verify Pattern 3 elements are present
        assert "fetch_tool_infos" in supervisor_code
        assert "async def run_supervisor" in supervisor_code
        assert "tool_infos: List[ToolInfo]" in supervisor_code
        assert "for server_url in MCP_SERVER_URLS" in supervisor_code
        assert "tools/list" in supervisor_code
        assert "Dynamic tool discovery" in supervisor_code or "Pattern 3" in supervisor_code

    def test_generated_code_has_mlflow_tracing(self, db: Session):
        """Test that generated code includes MLflow tracing."""
        # Create collection
        collection = Collection(name="Tracing Test", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        supervisor_code = files["supervisor.py"]

        # Verify MLflow tracing elements
        assert "import mlflow" in supervisor_code
        assert "mlflow.start_span" in supervisor_code
        assert "set_inputs" in supervisor_code
        assert "set_outputs" in supervisor_code

    def test_generated_code_has_error_handling(self, db: Session):
        """Test that generated code includes error handling."""
        # Create collection
        collection = Collection(name="Error Handling Test", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        supervisor_code = files["supervisor.py"]

        # Verify error handling
        assert "try:" in supervisor_code
        assert "except" in supervisor_code
        assert "HTTPException" in supervisor_code

    def test_generated_requirements_has_dependencies(self, db: Session):
        """Test that generated requirements.txt includes all dependencies."""
        # Create collection
        collection = Collection(name="Dependencies Test", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        requirements = files["requirements.txt"]

        # Verify dependencies
        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "httpx" in requirements
        assert "mlflow" in requirements
        assert "pydantic" in requirements

    def test_generated_app_yaml_has_required_fields(self, db: Session):
        """Test that generated app.yaml has required Databricks Apps fields."""
        # Create collection
        collection = Collection(name="App YAML Test", description="Test")
        db.add(collection)
        db.commit()

        service = GeneratorService()
        files = service.generate_supervisor_code(collection.id)

        app_yaml = files["app.yaml"]

        # Verify required fields
        assert "name:" in app_yaml
        assert "command:" in app_yaml
        assert "env:" in app_yaml
        assert "DATABRICKS_HOST" in app_yaml
        assert "DATABRICKS_TOKEN" in app_yaml
        assert "LLM_ENDPOINT" in app_yaml
        assert "MCP_SERVER_URLS" in app_yaml
        assert "resources:" in app_yaml
        assert "health_check:" in app_yaml
        assert "port:" in app_yaml
