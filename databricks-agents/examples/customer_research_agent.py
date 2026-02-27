"""
Example: Customer Research Agent

A Databricks App that uses the databricks-agents framework to create
a discoverable agent with tool capabilities.
"""

from databricks_agents import AgentApp

# Create the agent app
app = AgentApp(
    name="customer_research",
    description="Research customer information and market trends",
    capabilities=["search", "analysis", "research"],
)


@app.tool(description="Search for companies by industry")
async def search_companies(industry: str, limit: int = 10) -> dict:
    """
    Search for companies in a specific industry.
    
    Args:
        industry: Industry sector to search (e.g., "technology", "healthcare")
        limit: Maximum number of results to return
    
    Returns:
        Dictionary with company search results
    """
    # In a real implementation, this would query a database or API
    return {
        "industry": industry,
        "results": [
            {"name": f"Company {i}", "sector": industry}
            for i in range(1, min(limit, 5) + 1)
        ],
        "total": limit,
    }


@app.tool(description="Analyze market trends for a sector")
async def analyze_trends(sector: str, timeframe: str = "1y") -> dict:
    """
    Analyze market trends for a business sector.
    
    Args:
        sector: Business sector to analyze
        timeframe: Time period (e.g., "1y", "6m", "3m")
    
    Returns:
        Dictionary with trend analysis
    """
    # In a real implementation, this would analyze actual market data
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


# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
