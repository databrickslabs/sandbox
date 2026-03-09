"""Tests for UCFunctionAdapter — UC Functions to MCP tool conversion."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import List, Optional

from dbx_agent_app.mcp.uc_functions import UCFunctionAdapter


@dataclass
class _FakeParam:
    name: str
    type_name: str
    comment: str = ""
    default_value: Optional[str] = None


@dataclass
class _FakeInputParams:
    parameters: List[_FakeParam]


@dataclass
class _FakeFunction:
    name: str
    full_name: str
    comment: str = ""
    input_params: Optional[_FakeInputParams] = None


# --- UC type → JSON Schema type mapping ---


class TestTypeMapping:
    """Test _map_uc_type_to_json_type."""

    def setup_method(self):
        self.adapter = UCFunctionAdapter()

    def test_string_types(self):
        assert self.adapter._map_uc_type_to_json_type("STRING") == "string"
        assert self.adapter._map_uc_type_to_json_type("VARCHAR") == "string"
        assert self.adapter._map_uc_type_to_json_type("CHAR") == "string"

    def test_integer_types(self):
        assert self.adapter._map_uc_type_to_json_type("BIGINT") == "integer"
        assert self.adapter._map_uc_type_to_json_type("INT") == "integer"
        assert self.adapter._map_uc_type_to_json_type("INTEGER") == "integer"
        assert self.adapter._map_uc_type_to_json_type("SMALLINT") == "integer"
        assert self.adapter._map_uc_type_to_json_type("TINYINT") == "integer"

    def test_number_types(self):
        assert self.adapter._map_uc_type_to_json_type("DOUBLE") == "number"
        assert self.adapter._map_uc_type_to_json_type("FLOAT") == "number"
        assert self.adapter._map_uc_type_to_json_type("DECIMAL") == "number"

    def test_boolean(self):
        assert self.adapter._map_uc_type_to_json_type("BOOLEAN") == "boolean"

    def test_complex_types(self):
        assert self.adapter._map_uc_type_to_json_type("ARRAY") == "array"
        assert self.adapter._map_uc_type_to_json_type("MAP") == "object"
        assert self.adapter._map_uc_type_to_json_type("STRUCT") == "object"

    def test_date_types_map_to_string(self):
        assert self.adapter._map_uc_type_to_json_type("DATE") == "string"
        assert self.adapter._map_uc_type_to_json_type("TIMESTAMP") == "string"

    def test_unknown_defaults_to_string(self):
        assert self.adapter._map_uc_type_to_json_type("CUSTOM_TYPE") == "string"

    def test_case_insensitive(self):
        assert self.adapter._map_uc_type_to_json_type("string") == "string"
        assert self.adapter._map_uc_type_to_json_type("Int") == "integer"


# --- Function to MCP tool conversion ---


class TestConvertFunctionToTool:
    """Test _convert_function_to_tool."""

    def setup_method(self):
        self.adapter = UCFunctionAdapter()

    def test_basic_conversion(self):
        func = _FakeFunction(
            name="main.funcs.calculate",
            full_name="main.funcs.calculate",
            comment="Calculate a value",
            input_params=_FakeInputParams(parameters=[
                _FakeParam(name="amount", type_name="DOUBLE", comment="The amount"),
                _FakeParam(name="rate", type_name="DOUBLE", comment="The rate"),
            ]),
        )

        tool = self.adapter._convert_function_to_tool(func)

        assert tool is not None
        assert tool["name"] == "calculate"
        assert tool["description"] == "Calculate a value"
        assert tool["full_name"] == "main.funcs.calculate"
        assert tool["source"] == "unity_catalog"

        props = tool["inputSchema"]["properties"]
        assert props["amount"]["type"] == "number"
        assert props["rate"]["type"] == "number"

    def test_required_params(self):
        """Parameters without defaults are marked required."""
        func = _FakeFunction(
            name="main.funcs.search",
            full_name="main.funcs.search",
            comment="Search",
            input_params=_FakeInputParams(parameters=[
                _FakeParam(name="query", type_name="STRING"),
                _FakeParam(name="limit", type_name="INT", default_value="10"),
            ]),
        )

        tool = self.adapter._convert_function_to_tool(func)

        required = tool["inputSchema"]["required"]
        assert "query" in required
        assert "limit" not in required

    def test_no_params(self):
        """Function with no parameters still converts."""
        func = _FakeFunction(
            name="main.funcs.get_time",
            full_name="main.funcs.get_time",
            comment="Get current time",
        )

        tool = self.adapter._convert_function_to_tool(func)

        assert tool is not None
        assert tool["inputSchema"]["properties"] == {}

    def test_no_comment_uses_default_description(self):
        """Missing comment generates a default description."""
        func = _FakeFunction(
            name="main.funcs.mystery",
            full_name="main.funcs.mystery",
            comment="",
        )

        tool = self.adapter._convert_function_to_tool(func)

        assert "mystery" in tool["description"]


# --- discover_functions ---


class TestDiscoverFunctions:
    """Test discover_functions with mocked WorkspaceClient."""

    def test_discovers_functions(self):
        adapter = UCFunctionAdapter()
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_client.functions.list.return_value = [
            _FakeFunction(
                name="calc",
                full_name="main.funcs.calc",
                comment="Calculate",
                input_params=_FakeInputParams(parameters=[
                    _FakeParam(name="x", type_name="INT"),
                ]),
            ),
            _FakeFunction(
                name="format",
                full_name="main.funcs.format",
                comment="Format data",
            ),
        ]

        tools = adapter.discover_functions("main", "funcs")

        assert len(tools) == 2
        assert tools[0]["name"] == "calc"
        assert tools[1]["name"] == "format"

    def test_skips_system_functions(self):
        adapter = UCFunctionAdapter()
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_client.functions.list.return_value = [
            _FakeFunction(
                name="system.builtin",
                full_name="system.builtin",
                comment="System function",
            ),
            _FakeFunction(
                name="user_func",
                full_name="main.funcs.user_func",
                comment="User function",
            ),
        ]

        tools = adapter.discover_functions("main", "funcs")

        assert len(tools) == 1
        assert tools[0]["name"] == "user_func"

    def test_name_pattern_filter(self):
        adapter = UCFunctionAdapter()
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_client.functions.list.return_value = [
            _FakeFunction(name="calc_tax", full_name="main.funcs.calc_tax", comment="Tax"),
            _FakeFunction(name="format_date", full_name="main.funcs.format_date", comment="Date"),
        ]

        tools = adapter.discover_functions("main", "funcs", name_pattern="calc")

        assert len(tools) == 1
        assert tools[0]["name"] == "calc_tax"

    def test_handles_listing_error(self):
        adapter = UCFunctionAdapter()
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_client.functions.list.side_effect = Exception("Access denied")

        tools = adapter.discover_functions("main", "funcs")
        assert tools == []
