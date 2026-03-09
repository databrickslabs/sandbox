"""
Tool specification parser and normalizer.

This module handles parsing tool specifications from MCP servers
and normalizing them to the registry's schema format.
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class NormalizedTool:
    """
    Normalized tool specification for registry storage.

    Attributes:
        name: Tool identifier (required)
        description: Human-readable description (optional)
        parameters: JSON Schema string for parameters (optional)
    """

    name: str
    description: Optional[str]
    parameters: Optional[str]


class ToolParser:
    """
    Parser for tool specifications from MCP servers.

    Handles extracting and normalizing tool metadata from various
    MCP server response formats.
    """

    @staticmethod
    def extract_parameters_schema(input_schema: Dict[str, Any]) -> str:
        """
        Extract parameters schema from MCP input schema.

        Converts the input schema to a JSON string for storage.
        Handles missing or invalid schemas gracefully.

        Args:
            input_schema: MCP tool input schema (JSON Schema format)

        Returns:
            JSON string of parameters schema

        Example:
            >>> schema = {"type": "object", "properties": {"query": {"type": "string"}}}
            >>> result = ToolParser.extract_parameters_schema(schema)
            >>> print(result)
            '{"type": "object", "properties": {"query": {"type": "string"}}}'
        """
        if not input_schema or not isinstance(input_schema, dict):
            return "{}"

        try:
            return json.dumps(input_schema, separators=(",", ":"))
        except (TypeError, ValueError):
            return "{}"

    @staticmethod
    def normalize_description(description: Optional[str]) -> Optional[str]:
        """
        Normalize tool description.

        Handles missing descriptions, trims whitespace, and limits length.

        Args:
            description: Raw description from MCP server

        Returns:
            Normalized description or None
        """
        if not description:
            return None

        normalized = description.strip()

        if not normalized:
            return None

        # Limit description length to prevent database issues
        max_length = 5000
        if len(normalized) > max_length:
            normalized = normalized[:max_length] + "..."

        return normalized

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize tool name.

        Ensures name is valid and consistent.

        Args:
            name: Raw tool name from MCP server

        Returns:
            Normalized tool name

        Raises:
            ValueError: If name is empty or invalid
        """
        if not name or not isinstance(name, str):
            raise ValueError("Tool name is required and must be a string")

        normalized = name.strip()

        if not normalized:
            raise ValueError("Tool name cannot be empty")

        # Limit name length
        max_length = 255
        if len(normalized) > max_length:
            normalized = normalized[:max_length]

        return normalized

    @staticmethod
    def parse_tool(tool_data: Dict[str, Any]) -> NormalizedTool:
        """
        Parse and normalize a tool specification.

        Converts raw MCP tool data into a normalized format for registry storage.

        Args:
            tool_data: Raw tool data from MCP server

        Returns:
            NormalizedTool with validated and normalized fields

        Raises:
            ValueError: If tool data is invalid or missing required fields

        Example:
            >>> tool_data = {
            ...     "name": "search_experts",
            ...     "description": "Search for experts by keyword",
            ...     "inputSchema": {
            ...         "type": "object",
            ...         "properties": {"query": {"type": "string"}}
            ...     }
            ... }
            >>> tool = ToolParser.parse_tool(tool_data)
            >>> print(tool.name)
            search_experts
        """
        if not isinstance(tool_data, dict):
            raise ValueError("Tool data must be a dictionary")

        # Extract and normalize name (required)
        raw_name = tool_data.get("name")
        name = ToolParser.normalize_name(raw_name)

        # Extract and normalize description (optional)
        raw_description = tool_data.get("description")
        description = ToolParser.normalize_description(raw_description)

        # Extract and normalize parameters (optional)
        input_schema = tool_data.get("inputSchema", {})
        parameters = ToolParser.extract_parameters_schema(input_schema)

        return NormalizedTool(
            name=name,
            description=description,
            parameters=parameters,
        )


def normalize_tool_spec(
    name: str,
    description: Optional[str] = None,
    input_schema: Optional[Dict[str, Any]] = None,
) -> NormalizedTool:
    """
    Convenience function to normalize a tool specification.

    Args:
        name: Tool name
        description: Tool description (optional)
        input_schema: Tool parameters schema (optional)

    Returns:
        NormalizedTool instance

    Example:
        >>> tool = normalize_tool_spec(
        ...     name="my_tool",
        ...     description="Does something useful",
        ...     input_schema={"type": "object"}
        ... )
        >>> print(tool.name)
        my_tool
    """
    tool_data = {"name": name}

    if description:
        tool_data["description"] = description

    if input_schema:
        tool_data["inputSchema"] = input_schema

    return ToolParser.parse_tool(tool_data)
