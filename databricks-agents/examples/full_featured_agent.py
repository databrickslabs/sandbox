"""
Example: Full-Featured Agent

Demonstrates all framework capabilities:
- AgentApp with tools
- Unity Catalog registration
- MCP server
- UC Functions integration
"""

from contextlib import asynccontextmanager
from databricks_agents import AgentApp
from databricks_agents.mcp import UCFunctionAdapter


@asynccontextmanager
async def lifespan(app):
    """Discover UC Functions and make them available as tools on startup."""
    try:
        adapter = UCFunctionAdapter()

        # Discover functions from a UC schema
        functions = adapter.discover_functions(
            catalog="main",
            schema="data_functions"
        )

        print(f"Discovered {len(functions)} UC Functions")

        # Note: In a full implementation, you'd register these as tools
        # For now, they're available via the MCP server

    except Exception as e:
        print(f"UC Functions discovery failed: {e}")

    yield


# Create agent with full configuration
app = AgentApp(
    name="data_processor",
    description="Process and analyze data with UC Functions",
    capabilities=["data_processing", "analysis", "uc_integration"],
    uc_catalog="main",
    uc_schema="agents",
    auto_register=True,  # Auto-register in UC on startup
    enable_mcp=True,     # Enable MCP server at /api/mcp
    lifespan=lifespan,
)


# Register custom tools
@app.tool(description="Process CSV data and return statistics")
async def process_csv(file_path: str, calculate_stats: bool = True) -> dict:
    """Process CSV file and optionally calculate statistics."""
    # In production, this would actually read and process the file
    return {
        "file_path": file_path,
        "rows_processed": 1000,
        "columns": ["id", "name", "value"],
        "statistics": {
            "mean": 45.6,
            "median": 42.0,
            "std_dev": 12.3
        } if calculate_stats else None
    }


@app.tool(description="Run data quality checks")
async def check_data_quality(
    table_name: str,
    checks: list[str] = ["nulls", "duplicates", "outliers"]
) -> dict:
    """Run data quality checks on a table."""
    results = {}
    for check in checks:
        results[check] = {
            "passed": True,
            "issues_found": 0,
            "severity": "none"
        }
    return {
        "table": table_name,
        "checks": results,
        "overall_status": "passed"
    }


# Run the agent
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🤖 Full-Featured Agent Starting")
    print("="*60)
    print("\nFeatures enabled:")
    print("  ✓ Agent card at /.well-known/agent.json")
    print("  ✓ OIDC config at /.well-known/openid-configuration")
    print("  ✓ Health check at /health")
    print("  ✓ MCP server at /api/mcp")
    print("  ✓ Custom tools at /api/tools/*")
    print("  ✓ Unity Catalog registration (on deployment)")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
