"""
Admin endpoints for initializing demo data using Databricks SQL Warehouse.
"""

import json
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.db_adapter import WarehouseDB

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post(
    "/initialize-demo-data",
    status_code=status.HTTP_200_OK,
    summary="Initialize Demo Data",
    description="Populate the registry with demo apps, MCP servers, and tools"
)
def initialize_demo_data() -> Dict[str, Any]:
    """
    Initialize the registry with demo data including:
    - Guidepoint workspace apps
    - MCP servers
    - Tools

    Returns counts of created items.
    """
    stats = {
        "apps_created": 0,
        "servers_created": 0,
        "tools_created": 0,
        "collections_created": 0,
        "errors": []
    }

    # Demo apps
    demo_apps = [
        {
            "name": "guidepoint-sgp-research",
            "owner": "Guidepoint",
            "url": "https://guidepoint-sgp-research-7474660127789418.aws.databricksapps.com",
            "tags": "research,transcripts,experts,sgp",
        },
        {
            "name": "guidepoint-agent-discovery",
            "owner": "Guidepoint",
            "url": "https://guidepoint-agent-discovery-7474660127789418.aws.databricksapps.com",
            "tags": "discovery,agents,tools",
        },
        {
            "name": "guidepoint-chat-ui",
            "owner": "Guidepoint",
            "url": "https://guidepoint-chat-ui-7474660127789418.aws.databricksapps.com",
            "tags": "ui,chat,interface",
        }
    ]

    # Create apps
    for app_data in demo_apps:
        try:
            WarehouseDB.create_app(**app_data)
            stats["apps_created"] += 1
        except Exception as e:
            stats["errors"].append(f"Error creating app {app_data['name']}: {str(e)}")

    # Demo MCP servers
    try:
        server = WarehouseDB.create_mcp_server(
            server_url="https://guidepoint-sgp-research-7474660127789418.aws.databricksapps.com/mcp",
            kind="managed"
        )
        stats["servers_created"] += 1
        server_id = server["id"]

        # Demo tools
        demo_tools = [
            {
                "mcp_server_id": server_id,
                "name": "search_transcripts",
                "description": "Search expert transcripts by keywords, topics, or expert criteria.",
                "parameters": json.dumps({
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                })
            },
            {
                "mcp_server_id": server_id,
                "name": "get_expert_profile",
                "description": "Get detailed profile information for a specific expert.",
                "parameters": json.dumps({
                    "type": "object",
                    "properties": {
                        "expert_id": {"type": "string", "description": "Expert ID"}
                    },
                    "required": ["expert_id"]
                })
            },
            {
                "mcp_server_id": server_id,
                "name": "find_experts",
                "description": "Find experts by industry, topic, or expertise area.",
                "parameters": json.dumps({
                    "type": "object",
                    "properties": {
                        "industry": {"type": "string"},
                        "expertise": {"type": "string"},
                        "limit": {"type": "integer", "default": 20}
                    }
                })
            }
        ]

        for tool_data in demo_tools:
            try:
                WarehouseDB.create_tool(**tool_data)
                stats["tools_created"] += 1
            except Exception as e:
                stats["errors"].append(f"Error creating tool {tool_data['name']}: {str(e)}")

    except Exception as e:
        stats["errors"].append(f"Error creating MCP server: {str(e)}")

    # Create a demo collection
    try:
        WarehouseDB.create_collection(
            name="Research Tools",
            description="Collection of tools for searching expert transcripts and profiles"
        )
        stats["collections_created"] = 1
    except Exception as e:
        stats["errors"].append(f"Error creating demo collection: {str(e)}")

    return {
        "success": True,
        "message": "Demo data initialized successfully",
        "stats": stats
    }


@router.delete(
    "/clear-all-data",
    status_code=status.HTTP_200_OK,
    summary="Clear All Data",
    description="Delete all apps, servers, tools, and collections (for development only)"
)
def clear_all_data() -> Dict[str, Any]:
    """
    Clear all data from the registry.
    WARNING: This is destructive and cannot be undone!
    """
    # This would require implementing delete_all methods in WarehouseDB
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Clear all data not yet implemented for warehouse backend"
    )
