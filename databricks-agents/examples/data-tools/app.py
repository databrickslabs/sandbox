"""Multi-tool agent with MCP -- search, analysis, and data quality tools."""
from dbx_agent_app import app_agent, AgentRequest, AgentResponse


@app_agent(
    name="data_tools",
    description="Multi-tool data agent for search, analysis, and quality checks",
    capabilities=["search", "analysis", "data_processing"],
    auto_register=False,
    enable_mcp=True,
)
async def data_tools(request: AgentRequest) -> AgentResponse:
    """Route to search_companies by default."""
    result = await search_companies(request.last_user_message)
    return AgentResponse.from_dict(result)


@data_tools.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    """Search for companies in a specific industry."""
    return {
        "industry": industry,
        "results": [
            {"name": f"Company {i}", "sector": industry, "revenue": f"${i * 50}M"}
            for i in range(1, min(limit, 5) + 1)
        ],
        "total": limit,
    }


@data_tools.tool(description="Analyze market trends for a sector")
async def analyze_trends(sector: str, timeframe: str = "1y") -> dict:
    """Analyze market trends for a business sector."""
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


@data_tools.tool(description="Run data quality checks on a table")
async def check_data_quality(
    table_name: str,
    checks: list[str] = ["nulls", "duplicates", "outliers"],
) -> dict:
    """Run data quality checks on a table."""
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


app = data_tools.app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
