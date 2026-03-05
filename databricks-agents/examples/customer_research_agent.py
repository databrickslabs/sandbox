"""
Example: Customer Research Agent

A Databricks App that uses the databricks-agent-deploy framework to create
a discoverable agent with tool capabilities.
"""

from databricks_agents import AgentApp

agent = AgentApp(
    name="customer_research",
    description="Research customer information and market trends",
    capabilities=["search", "analysis", "research"],
)


@agent.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    """
    Search for companies in a specific industry.

    Args:
        industry: Industry sector to search (e.g., "technology", "healthcare")
        limit: Maximum number of results to return

    Returns:
        Dictionary with company search results
    """
    return {
        "industry": industry,
        "results": [
            {"name": f"Company {i}", "sector": industry}
            for i in range(1, min(limit, 5) + 1)
        ],
        "total": limit,
    }


@agent.tool(description="Analyze market trends for a sector")
async def analyze_trends(sector: str, timeframe: str = "1y") -> dict:
    """
    Analyze market trends for a business sector.

    Args:
        sector: Business sector to analyze
        timeframe: Time period (e.g., "1y", "6m", "3m")

    Returns:
        Dictionary with trend analysis
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


app = agent.as_fastapi()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
