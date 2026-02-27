"""
Tests for Tools endpoints (read-only).
"""

import pytest
from app.models import App, MCPServer, Tool
from app.models.mcp_server import MCPServerKind


def test_list_tools_empty(client, db):
    """Test listing tools when none exist."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["total_pages"] == 1


def test_list_tools_with_data(client, db, sample_tool):
    """Test listing tools with sample data."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == sample_tool.name


def test_list_tools_filter_by_server(client, db, sample_tool):
    """Test filtering tools by MCP server ID."""
    response = client.get(f"/api/tools?mcp_server_id={sample_tool.mcp_server_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == sample_tool.id


def test_list_tools_filter_by_name(client, db, sample_tool):
    """Test filtering tools by name."""
    response = client.get("/api/tools?name=test")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


def test_list_tools_search(client, db):
    """Test full-text search on tool name and description."""
    # Create app and server
    app = App(name="test-app", owner="owner@example.com")
    db.add(app)
    db.commit()
    db.refresh(app)

    server = MCPServer(
        app_id=app.id,
        server_url="https://example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    # Create tools with different names and descriptions
    tool1 = Tool(
        mcp_server_id=server.id,
        name="search_transcripts",
        description="Search through expert call transcripts",
    )
    tool2 = Tool(
        mcp_server_id=server.id,
        name="find_experts",
        description="Find experts in the database",
    )
    tool3 = Tool(
        mcp_server_id=server.id,
        name="analyze_data",
        description="Analyze research data",
    )
    db.add_all([tool1, tool2, tool3])
    db.commit()

    # Search for "expert" (matches tool1 description and tool2 name)
    response = client.get("/api/tools?search=expert")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    names = {item["name"] for item in data["items"]}
    assert names == {"search_transcripts", "find_experts"}

    # Search for "research" (matches tool3 description)
    response = client.get("/api/tools?search=research")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "analyze_data"


def test_list_tools_filter_by_tags(client, db):
    """Test filtering tools by app tags."""
    # Create apps with tags
    app1 = App(name="app1", owner="owner1@example.com", tags="research,analysis")
    app2 = App(name="app2", owner="owner2@example.com", tags="automation,testing")
    db.add_all([app1, app2])
    db.commit()

    # Create servers
    server1 = MCPServer(
        app_id=app1.id,
        server_url="https://app1.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    server2 = MCPServer(
        app_id=app2.id,
        server_url="https://app2.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    db.add_all([server1, server2])
    db.commit()

    # Create tools
    tool1 = Tool(mcp_server_id=server1.id, name="tool1", description="Research tool")
    tool2 = Tool(mcp_server_id=server2.id, name="tool2", description="Automation tool")
    db.add_all([tool1, tool2])
    db.commit()

    # Filter by "research" tag
    response = client.get("/api/tools?tags=research")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "tool1"

    # Filter by "automation" tag
    response = client.get("/api/tools?tags=automation")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "tool2"

    # Filter by multiple tags (comma-separated)
    response = client.get("/api/tools?tags=research,automation")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


def test_list_tools_filter_by_owner(client, db):
    """Test filtering tools by app owner."""
    # Create apps with different owners
    app1 = App(name="app1", owner="alice@example.com")
    app2 = App(name="app2", owner="bob@example.com")
    db.add_all([app1, app2])
    db.commit()

    # Create servers
    server1 = MCPServer(
        app_id=app1.id,
        server_url="https://app1.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    server2 = MCPServer(
        app_id=app2.id,
        server_url="https://app2.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    db.add_all([server1, server2])
    db.commit()

    # Create tools
    tool1 = Tool(mcp_server_id=server1.id, name="alice_tool", description="Alice's tool")
    tool2 = Tool(mcp_server_id=server2.id, name="bob_tool", description="Bob's tool")
    db.add_all([tool1, tool2])
    db.commit()

    # Filter by Alice's tools
    response = client.get("/api/tools?owner=alice")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "alice_tool"

    # Filter by Bob's tools
    response = client.get("/api/tools?owner=bob")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "bob_tool"


def test_list_tools_combined_filters(client, db):
    """Test combining multiple filters."""
    # Create app
    app = App(name="app", owner="owner@example.com", tags="research")
    db.add(app)
    db.commit()

    # Create server
    server = MCPServer(
        app_id=app.id,
        server_url="https://app.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    db.add(server)
    db.commit()

    # Create tools
    tool1 = Tool(
        mcp_server_id=server.id,
        name="search_experts",
        description="Search for experts",
    )
    tool2 = Tool(
        mcp_server_id=server.id,
        name="analyze_data",
        description="Analyze data",
    )
    db.add_all([tool1, tool2])
    db.commit()

    # Combine search + tags + owner
    response = client.get("/api/tools?search=expert&tags=research&owner=owner")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "search_experts"


def test_list_tools_pagination(client, db):
    """Test pagination with filtering."""
    # Create app and server
    app = App(name="app", owner="owner@example.com")
    db.add(app)
    db.commit()

    server = MCPServer(
        app_id=app.id,
        server_url="https://app.example.com/mcp",
        kind=MCPServerKind.CUSTOM,
    )
    db.add(server)
    db.commit()

    # Create multiple tools
    for i in range(15):
        tool = Tool(
            mcp_server_id=server.id,
            name=f"tool_{i}",
            description=f"Tool {i}",
        )
        db.add(tool)
    db.commit()

    # Get first page
    response = client.get("/api/tools?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] == 2

    # Get second page
    response = client.get("/api/tools?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 15
    assert len(data["items"]) == 5
    assert data["page"] == 2


def test_get_tool_success(client, db, sample_tool):
    """Test getting a specific tool."""
    response = client.get(f"/api/tools/{sample_tool.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_tool.id
    assert data["name"] == sample_tool.name


def test_get_tool_not_found(client, db):
    """Test getting a non-existent tool."""
    response = client.get("/api/tools/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
