"""
Unit tests for tool parser.
"""

import pytest
import json

from app.services.tool_parser import (
    ToolParser,
    NormalizedTool,
    normalize_tool_spec,
)


class TestToolParser:
    """Tests for ToolParser class."""

    def test_extract_parameters_schema_valid(self):
        """Test extracting valid parameters schema."""
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }

        result = ToolParser.extract_parameters_schema(schema)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["type"] == "object"
        assert "query" in parsed["properties"]

    def test_extract_parameters_schema_empty(self):
        """Test extracting empty schema."""
        result = ToolParser.extract_parameters_schema({})

        assert result == "{}"

    def test_extract_parameters_schema_none(self):
        """Test handling None schema."""
        result = ToolParser.extract_parameters_schema(None)

        assert result == "{}"

    def test_extract_parameters_schema_invalid_type(self):
        """Test handling invalid schema type."""
        result = ToolParser.extract_parameters_schema("not a dict")

        assert result == "{}"

    def test_normalize_description_valid(self):
        """Test normalizing valid description."""
        description = "  Search for experts by keyword  "
        result = ToolParser.normalize_description(description)

        assert result == "Search for experts by keyword"

    def test_normalize_description_none(self):
        """Test handling None description."""
        result = ToolParser.normalize_description(None)

        assert result is None

    def test_normalize_description_empty(self):
        """Test handling empty description."""
        result = ToolParser.normalize_description("")

        assert result is None

    def test_normalize_description_whitespace_only(self):
        """Test handling whitespace-only description."""
        result = ToolParser.normalize_description("   \n\t   ")

        assert result is None

    def test_normalize_description_max_length(self):
        """Test description length limiting."""
        long_description = "x" * 6000
        result = ToolParser.normalize_description(long_description)

        assert len(result) <= 5003  # 5000 + "..."
        assert result.endswith("...")

    def test_normalize_name_valid(self):
        """Test normalizing valid name."""
        name = "  search_experts  "
        result = ToolParser.normalize_name(name)

        assert result == "search_experts"

    def test_normalize_name_empty_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolParser.normalize_name("")

        assert "required" in str(exc_info.value).lower()

    def test_normalize_name_none_raises_error(self):
        """Test that None name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolParser.normalize_name(None)

        assert "required" in str(exc_info.value)

    def test_normalize_name_whitespace_only_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolParser.normalize_name("   \n\t   ")

        assert "cannot be empty" in str(exc_info.value)

    def test_normalize_name_max_length(self):
        """Test name length limiting."""
        long_name = "x" * 300
        result = ToolParser.normalize_name(long_name)

        assert len(result) == 255

    def test_normalize_name_invalid_type_raises_error(self):
        """Test that invalid name type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolParser.normalize_name(123)

        assert "must be a string" in str(exc_info.value)

    def test_parse_tool_full_data(self):
        """Test parsing tool with all fields."""
        tool_data = {
            "name": "search_experts",
            "description": "Search for experts by keyword",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }

        result = ToolParser.parse_tool(tool_data)

        assert isinstance(result, NormalizedTool)
        assert result.name == "search_experts"
        assert result.description == "Search for experts by keyword"
        assert isinstance(result.parameters, str)
        parsed_params = json.loads(result.parameters)
        assert parsed_params["type"] == "object"

    def test_parse_tool_minimal_data(self):
        """Test parsing tool with only required fields."""
        tool_data = {"name": "minimal_tool"}

        result = ToolParser.parse_tool(tool_data)

        assert result.name == "minimal_tool"
        assert result.description is None
        assert result.parameters == "{}"

    def test_parse_tool_missing_name_raises_error(self):
        """Test that missing name raises ValueError."""
        tool_data = {
            "description": "Missing name",
            "inputSchema": {"type": "object"},
        }

        with pytest.raises(ValueError) as exc_info:
            ToolParser.parse_tool(tool_data)

        assert "required" in str(exc_info.value).lower()

    def test_parse_tool_invalid_data_type_raises_error(self):
        """Test that invalid data type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolParser.parse_tool("not a dict")

        assert "must be a dictionary" in str(exc_info.value)

    def test_parse_tool_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        tool_data = {"name": ""}

        with pytest.raises(ValueError) as exc_info:
            ToolParser.parse_tool(tool_data)

        assert "required" in str(exc_info.value).lower()

    def test_parse_tool_with_empty_description(self):
        """Test parsing tool with empty description."""
        tool_data = {
            "name": "test_tool",
            "description": "",
            "inputSchema": {},
        }

        result = ToolParser.parse_tool(tool_data)

        assert result.name == "test_tool"
        assert result.description is None  # Empty description becomes None

    def test_parse_tool_with_whitespace_trimming(self):
        """Test that name and description are trimmed."""
        tool_data = {
            "name": "  test_tool  ",
            "description": "  Test description  ",
        }

        result = ToolParser.parse_tool(tool_data)

        assert result.name == "test_tool"
        assert result.description == "Test description"


class TestNormalizeToolSpec:
    """Tests for normalize_tool_spec convenience function."""

    def test_normalize_tool_spec_all_fields(self):
        """Test normalizing tool spec with all fields."""
        result = normalize_tool_spec(
            name="my_tool",
            description="Does something useful",
            input_schema={"type": "object"},
        )

        assert isinstance(result, NormalizedTool)
        assert result.name == "my_tool"
        assert result.description == "Does something useful"
        parsed_params = json.loads(result.parameters)
        assert parsed_params["type"] == "object"

    def test_normalize_tool_spec_minimal(self):
        """Test normalizing tool spec with only name."""
        result = normalize_tool_spec(name="minimal_tool")

        assert result.name == "minimal_tool"
        assert result.description is None
        assert result.parameters == "{}"

    def test_normalize_tool_spec_with_description_only(self):
        """Test normalizing tool spec with name and description."""
        result = normalize_tool_spec(
            name="my_tool",
            description="Has a description",
        )

        assert result.name == "my_tool"
        assert result.description == "Has a description"
        assert result.parameters == "{}"

    def test_normalize_tool_spec_with_schema_only(self):
        """Test normalizing tool spec with name and schema."""
        result = normalize_tool_spec(
            name="my_tool",
            input_schema={"type": "string"},
        )

        assert result.name == "my_tool"
        assert result.description is None
        parsed_params = json.loads(result.parameters)
        assert parsed_params["type"] == "string"

    def test_normalize_tool_spec_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError):
            normalize_tool_spec(name="")


class TestNormalizedTool:
    """Tests for NormalizedTool dataclass."""

    def test_normalized_tool_creation(self):
        """Test creating NormalizedTool instance."""
        tool = NormalizedTool(
            name="test_tool",
            description="A test",
            parameters='{"type": "object"}',
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test"
        assert tool.parameters == '{"type": "object"}'

    def test_normalized_tool_optional_fields(self):
        """Test NormalizedTool with None optional fields."""
        tool = NormalizedTool(
            name="test_tool",
            description=None,
            parameters=None,
        )

        assert tool.name == "test_tool"
        assert tool.description is None
        assert tool.parameters is None
