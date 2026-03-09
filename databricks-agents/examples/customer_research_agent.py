"""
Example: Customer Research Agent

A Databricks App that uses the @app_agent decorator to create
a discoverable agent with tool capabilities.
"""

from databricks_agents import app_agent, AgentRequest, AgentResponse


@app_agent(
    name="customer_research",
    description="Research customer information and market trends",
    capabilities=["search", "analysis", "research"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    """Route to search_companies by default."""
    result = await search_companies(request.last_user_message)
    return AgentResponse.from_dict(result)


@customer_research.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    """Search for companies in a specific industry."""
    return {
        "industry": industry,
        "results": [
            {"name": f"Company {i}", "sector": industry}
            for i in range(1, min(limit, 5) + 1)
        ],
        "total": limit,
    }


@customer_research.tool(description="Analyze market trends for a sector")
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


app = customer_research.app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
