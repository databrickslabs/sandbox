"""
Tests for AgentApp core functionality.
"""

import pytest
from fastapi.testclient import TestClient

from databricks_agents import AgentApp


def test_agent_app_creation():
    """Test creating a basic agent app."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    assert app.agent_metadata.name == "test_agent"
    assert app.agent_metadata.description == "Test agent"
    assert app.agent_metadata.capabilities == ["test"]


def test_agent_card_endpoint():
    """Test that agent card endpoint is auto-generated."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    client = TestClient(app)
    response = client.get("/.well-known/agent.json")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["name"] == "test_agent"
    assert data["description"] == "Test agent"
    assert data["capabilities"] == ["test"]
    assert "endpoints" in data
    assert "tools" in data


def test_openid_config_endpoint():
    """Test that OIDC configuration endpoint is auto-generated."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    client = TestClient(app)
    response = client.get("/.well-known/openid-configuration")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data


def test_health_endpoint():
    """Test that health check endpoint is auto-generated."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["agent"] == "test_agent"


def test_tool_registration():
    """Test registering a tool with the agent."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    @app.tool(description="Test tool")
    async def test_tool(param: str) -> dict:
        return {"result": param}
    
    # Check tool is registered in agent metadata
    assert len(app.agent_metadata.tools) == 1
    tool = app.agent_metadata.tools[0]
    assert tool.name == "test_tool"
    assert tool.description == "Test tool"
    
    # Check tool endpoint was created
    client = TestClient(app)
    response = client.post("/api/tools/test_tool", json={"param": "value"})
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "value"


def test_tool_in_agent_card():
    """Test that tools appear in the agent card."""
    app = AgentApp(
        name="test_agent",
        description="Test agent",
        capabilities=["test"],
    )
    
    @app.tool(description="Test tool")
    async def test_tool(param: str) -> dict:
        return {"result": param}
    
    client = TestClient(app)
    response = client.get("/.well-known/agent.json")
    data = response.json()
    
    assert len(data["tools"]) == 1
    tool = data["tools"][0]
    assert tool["name"] == "test_tool"
    assert tool["description"] == "Test tool"
    assert "parameters" in tool
