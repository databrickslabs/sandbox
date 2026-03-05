"""Multi-tool agent with MCP -- search, analysis, and data quality tools."""
from databricks_agents import AgentApp

agent = AgentApp(
    name="data_tools",
    description="Multi-tool data agent for search, analysis, and quality checks",
    capabilities=["search", "analysis", "data_processing"],
    auto_register=False,
    enable_mcp=True,
)


@agent.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    """Search for companies in a specific industry.

    Args:
        industry: Industry sector to search (e.g., "technology", "healthcare")
        limit: Maximum number of results to return
    """
    return {
        "industry": industry,
        "results": [
            {"name": f"Company {i}", "sector": industry, "revenue": f"${i * 50}M"}
            for i in range(1, min(limit, 5) + 1)
        ],
        "total": limit,
    }


@agent.tool(description="Analyze market trends for a sector")
async def analyze_trends(sector: str, timeframe: str = "1y") -> dict:
    """Analyze market trends for a business sector.

    Args:
        sector: Business sector to analyze
        timeframe: Time period (e.g., "1y", "6m", "3m")
    """
    return {
        "sector": sector,
        "timeframe": timeframe,
        "trend": "positive",
        "growth_rate": 12.5,
        "insights": [
            "Strong demand growth",
            "Increasing market competition",
            "Technology adoption accelerating",
        ],
    }


@agent.tool(description="Run data quality checks on a table")
async def check_data_quality(
    table_name: str,
    checks: list[str] = ["nulls", "duplicates", "outliers"],
) -> dict:
    """Run data quality checks on a table.

    Args:
        table_name: Fully qualified table name
        checks: List of checks to run (nulls, duplicates, outliers)
    """
    results = {}
    for check in checks:
        results[check] = {
            "passed": True,
            "issues_found": 0,
            "severity": "none",
        }
    return {
        "table": table_name,
        "checks": results,
        "overall_status": "passed",
    }


app = agent.as_fastapi()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
