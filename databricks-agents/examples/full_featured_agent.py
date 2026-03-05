"""
Example: Full-Featured Agent with MCP

Demonstrates the recommended pattern:
- Plain FastAPI app with /invocations
- add_agent_card() for platform discoverability
- add_mcp_endpoints() for MCP-aware clients
- Tools defined as plain async functions
"""

import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from databricks_agents import add_agent_card, add_mcp_endpoints


app = FastAPI()


# --- Define your tools as plain async functions ---

async def process_csv(file_path: str, calculate_stats: bool = True) -> dict:
    """Process CSV file and optionally calculate statistics."""
    return {
        "file_path": file_path,
        "rows_processed": 1000,
        "columns": ["id", "name", "value"],
        "statistics": {
            "mean": 45.6,
            "median": 42.0,
            "std_dev": 12.3,
        } if calculate_stats else None,
    }


async def check_data_quality(table_name: str) -> dict:
    """Run data quality checks on a table."""
    checks = ["nulls", "duplicates", "outliers"]
    return {
        "table": table_name,
        "checks": {c: {"passed": True, "issues_found": 0} for c in checks},
        "overall_status": "passed",
    }


# --- Standard Databricks /invocations endpoint ---

TOOL_DISPATCH = {
    "process_csv": process_csv,
    "check_data_quality": check_data_quality,
}


@app.post("/invocations")
async def invocations(request: Request):
    body = await request.json()

    # Extract last user message
    query = ""
    for item in reversed(body.get("input", [])):
        if isinstance(item, dict) and item.get("role") == "user":
            query = item.get("content", "")
            break

    if not query:
        return JSONResponse({"error": "No user message found"}, status_code=400)

    # Simple dispatch: call process_csv with the query as file_path
    result = await process_csv(file_path=query)

    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(result, indent=2)}],
            }
        ],
    }


# --- Make discoverable by Agent Platform ---

tools_metadata = [
    {
        "name": "process_csv",
        "description": "Process CSV data and return statistics",
        "function": process_csv,
        "parameters": {
            "file_path": {"type": "string", "required": True},
            "calculate_stats": {"type": "boolean", "required": False},
        },
    },
    {
        "name": "check_data_quality",
        "description": "Run data quality checks on a table",
        "function": check_data_quality,
        "parameters": {
            "table_name": {"type": "string", "required": True},
        },
    },
]

add_agent_card(
    app,
    name="data_processor",
    description="Process and analyze data",
    capabilities=["data_processing", "analysis"],
    tools=[{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tools_metadata],
)

add_mcp_endpoints(app, tools=tools_metadata)


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("Full-Featured Agent Starting")
    print("=" * 60)
    print("\nEndpoints:")
    print("  /.well-known/agent.json  — agent card (platform discovery)")
    print("  /health                  — health check")
    print("  /invocations             — Databricks standard protocol")
    print("  /api/mcp                 — MCP JSON-RPC server")
    print("  /api/mcp/tools           — MCP tool listing")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
