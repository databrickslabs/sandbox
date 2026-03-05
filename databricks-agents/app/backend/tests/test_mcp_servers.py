"""
Tests for MCP Server CRUD endpoints.
"""

import pytest


def test_list_mcp_servers_empty(client):
    """Test listing MCP servers when none exist."""
    response = client.get("/api/mcp_servers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_create_mcp_server(client, sample_app):
    """Test creating a new MCP server."""
    response = client.post(
        "/api/mcp_servers",
        json={
            "app_id": sample_app.id,
            "server_url": "https://example.com/mcp",
            "kind": "custom",
            "scopes": "read,write",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["server_url"] == "https://example.com/mcp"
    assert data["kind"] == "custom"
    assert "id" in data


def test_create_mcp_server_invalid_app_id(client):
    """Test creating MCP server with non-existent app fails."""
    response = client.post(
        "/api/mcp_servers",
        json={
            "app_id": 9999,
            "server_url": "https://example.com/mcp",
            "kind": "custom",
        },
    )
    assert response.status_code == 422


def test_get_mcp_server(client, sample_mcp_server):
    """Test getting a specific MCP server."""
    response = client.get(f"/api/mcp_servers/{sample_mcp_server.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_mcp_server.id
    assert data["server_url"] == sample_mcp_server.server_url


def test_get_mcp_server_not_found(client):
    """Test getting non-existent MCP server returns 404."""
    response = client.get("/api/mcp_servers/9999")
    assert response.status_code == 404


def test_update_mcp_server(client, sample_mcp_server):
    """Test updating an MCP server."""
    response = client.put(
        f"/api/mcp_servers/{sample_mcp_server.id}",
        json={"scopes": "read,write,admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scopes"] == "read,write,admin"


def test_delete_mcp_server(client, sample_mcp_server):
    """Test deleting an MCP server."""
    response = client.delete(f"/api/mcp_servers/{sample_mcp_server.id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/mcp_servers/{sample_mcp_server.id}")
    assert response.status_code == 404


def test_list_mcp_servers_filter_by_app_id(client, sample_app, sample_mcp_server):
    """Test filtering MCP servers by app_id."""
    response = client.get(f"/api/mcp_servers?app_id={sample_app.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["app_id"] == sample_app.id


def test_list_mcp_servers_filter_by_kind(client, sample_mcp_server):
    """Test filtering MCP servers by kind."""
    response = client.get("/api/mcp_servers?kind=custom")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["kind"] == "custom"
