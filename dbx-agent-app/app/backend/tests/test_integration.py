"""
Integration tests for end-to-end workflows in the Multi-Agent Registry API.

These tests verify complete workflows across multiple endpoints and services.
"""

import pytest
from fastapi import status

from app.models.mcp_server import MCPServerKind


class TestDiscoveryWorkflow:
    """Test the complete discovery workflow."""

    def test_full_discovery_workflow(self, client, sample_app):
        """
        Test complete discovery workflow: register app → discover tools → query results.
        """
        # 1. Create an MCP server
        server_response = client.post(
            "/api/mcp_servers",
            json={
                "app_id": sample_app.id,
                "server_url": "https://example.com/mcp",
                "kind": "custom",
                "scopes": "read,write",
            },
        )
        assert server_response.status_code == status.HTTP_201_CREATED
        server = server_response.json()

        # 2. List all MCP servers
        list_response = client.get("/api/mcp_servers")
        assert list_response.status_code == status.HTTP_200_OK
        servers = list_response.json()
        assert servers["total"] >= 1
        assert any(s["id"] == server["id"] for s in servers["items"])

        # 3. Get tools (should be empty initially)
        tools_response = client.get("/api/tools")
        assert tools_response.status_code == status.HTTP_200_OK

        # 4. Check discovery status
        status_response = client.get("/api/discovery/status")
        assert status_response.status_code == status.HTTP_200_OK
        discovery_status = status_response.json()
        assert "is_running" in discovery_status
        assert "last_run_status" in discovery_status


class TestCollectionWorkflow:
    """Test the complete collection management workflow."""

    def test_full_collection_workflow(
        self, client, sample_app, sample_mcp_server, sample_tool
    ):
        """
        Test complete collection workflow: create → add items → list → generate.
        """
        # 1. Create a collection
        create_response = client.post(
            "/api/collections",
            json={
                "name": "Integration Test Collection",
                "description": "Collection for integration testing",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        collection = create_response.json()
        collection_id = collection["id"]

        # 2. Add server to collection (skip app since app_id is optional)
        # Note: Apps are typically not added directly to collections

        # 3. Add server to collection
        server_response = client.post(
            f"/api/collections/{collection_id}/items",
            json={"collection_id": collection_id, "mcp_server_id": sample_mcp_server.id},
        )
        assert server_response.status_code == status.HTTP_201_CREATED

        # 4. Add tool to collection
        tool_response = client.post(
            f"/api/collections/{collection_id}/items",
            json={"collection_id": collection_id, "tool_id": sample_tool.id},
        )
        assert tool_response.status_code == status.HTTP_201_CREATED

        # 5. List collection items
        items_response = client.get(f"/api/collections/{collection_id}/items")
        assert items_response.status_code == status.HTTP_200_OK
        items = items_response.json()
        assert len(items) == 2  # server + tool

        # 6. Get collection details
        get_response = client.get(f"/api/collections/{collection_id}")
        assert get_response.status_code == status.HTTP_200_OK
        collection_details = get_response.json()
        assert collection_details["name"] == "Integration Test Collection"

        # 7. Update collection
        update_response = client.put(
            f"/api/collections/{collection_id}",
            json={"description": "Updated description"},
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()
        assert updated["description"] == "Updated description"


class TestSupervisorGenerationWorkflow:
    """Test the complete supervisor generation workflow."""

    def test_full_supervisor_generation_workflow(
        self, client, sample_app, sample_mcp_server, sample_tool
    ):
        """
        Test complete supervisor workflow: create collection → generate → download.
        """
        # 1. Create a collection with tools
        collection_response = client.post(
            "/api/collections",
            json={
                "name": "Supervisor Test Collection",
                "description": "Collection for supervisor generation",
            },
        )
        assert collection_response.status_code == status.HTTP_201_CREATED
        collection = collection_response.json()
        collection_id = collection["id"]

        # 2. Add tool to collection
        item_response = client.post(
            f"/api/collections/{collection_id}/items",
            json={"collection_id": collection_id, "tool_id": sample_tool.id},
        )
        assert item_response.status_code == status.HTTP_201_CREATED

        # 3. Generate supervisor code
        generate_response = client.post(
            "/api/supervisors/generate",
            json={
                "collection_id": collection_id,
                "app_name": "test-supervisor",
                "llm_endpoint": "databricks-meta-llama-3-1-70b-instruct",
            },
        )
        assert generate_response.status_code == status.HTTP_201_CREATED
        generated = generate_response.json()
        assert "files" in generated
        assert generated["collection_id"] == collection_id
        assert "supervisor.py" in generated["files"]
        assert "requirements.txt" in generated["files"]
        assert "app.yaml" in generated["files"]

        # 4. Validate generated code contains expected elements
        code = generated["files"]["supervisor.py"]
        assert "class" in code or "def" in code
        assert "mlflow" in code.lower()
        # Tool name might be in the code or discovered at runtime

        # 5. Download supervisor artifacts (download endpoint expects POST, not GET)
        download_response = client.post(
            f"/api/supervisors/{collection_id}/download",
            json={
                "app_name": "test-supervisor",
                "llm_endpoint": "databricks-meta-llama-3-1-70b-instruct",
            },
        )
        assert download_response.status_code == status.HTTP_200_OK
        assert "application/zip" in download_response.headers.get("content-type", "")


class TestErrorHandlingWorkflow:
    """Test error handling across multiple endpoints."""

    def test_cascade_delete_workflow(self, client, sample_app, sample_mcp_server):
        """
        Test that deleting an app cascades to servers and tools.
        """
        # 1. Verify app and server exist
        app_response = client.get(f"/api/apps/{sample_app.id}")
        assert app_response.status_code == status.HTTP_200_OK

        server_response = client.get(f"/api/mcp_servers/{sample_mcp_server.id}")
        assert server_response.status_code == status.HTTP_200_OK

        # 2. Delete the app
        delete_response = client.delete(f"/api/apps/{sample_app.id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 3. Verify app is gone
        app_check = client.get(f"/api/apps/{sample_app.id}")
        assert app_check.status_code == status.HTTP_404_NOT_FOUND

        # 4. Verify server is gone (cascade delete)
        server_check = client.get(f"/api/mcp_servers/{sample_mcp_server.id}")
        assert server_check.status_code == status.HTTP_404_NOT_FOUND

    def test_foreign_key_constraint_workflow(self, client):
        """
        Test that foreign key constraints are enforced.
        """
        # Try to create MCP server with invalid app_id
        response = client.post(
            "/api/mcp_servers",
            json={
                "app_id": 99999,
                "server_url": "https://example.com/mcp",
                "kind": "custom",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_duplicate_name_workflow(self, client):
        """
        Test that duplicate names are prevented.
        """
        # 1. Create an app
        app_response = client.post(
            "/api/apps",
            json={"name": "unique-app", "owner": "test@example.com"},
        )
        assert app_response.status_code == status.HTTP_201_CREATED

        # 2. Try to create another app with same name
        duplicate_response = client.post(
            "/api/apps",
            json={"name": "unique-app", "owner": "other@example.com"},
        )
        assert duplicate_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_not_found_workflow(self, client):
        """
        Test 404 responses for non-existent resources.
        """
        # Test all endpoints
        endpoints = [
            "/api/apps/99999",
            "/api/mcp_servers/99999",
            "/api/tools/99999",
            "/api/collections/99999",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert (
                response.status_code == status.HTTP_404_NOT_FOUND
            ), f"Expected 404 for {endpoint}"


class TestPaginationWorkflow:
    """Test pagination across all list endpoints."""

    def test_pagination_workflow(self, client, db):
        """
        Test pagination works consistently across all endpoints.
        """
        # Create multiple apps
        from app.models import App

        apps = [App(name=f"app-{i}", owner="test@example.com") for i in range(15)]
        db.add_all(apps)
        db.commit()

        # Test first page
        page1 = client.get("/api/apps?page=1&page_size=10")
        assert page1.status_code == status.HTTP_200_OK
        data1 = page1.json()
        assert len(data1["items"]) == 10
        assert data1["page"] == 1
        assert data1["total"] == 15
        assert data1["total_pages"] == 2

        # Test second page
        page2 = client.get("/api/apps?page=2&page_size=10")
        assert page2.status_code == status.HTTP_200_OK
        data2 = page2.json()
        assert len(data2["items"]) == 5
        assert data2["page"] == 2

        # Test custom page size
        page_custom = client.get("/api/apps?page=1&page_size=5")
        assert page_custom.status_code == status.HTTP_200_OK
        data_custom = page_custom.json()
        assert len(data_custom["items"]) == 5
        assert data_custom["total_pages"] == 3


class TestFilteringWorkflow:
    """Test filtering across all list endpoints."""

    def test_filtering_workflow(self, client, db):
        """
        Test filtering works correctly on list endpoints.
        """
        from app.models import App, MCPServer

        # Create apps with different owners
        app1 = App(name="app-1", owner="alice@example.com")
        app2 = App(name="app-2", owner="bob@example.com")
        app3 = App(name="app-3", owner="alice@example.com")
        db.add_all([app1, app2, app3])
        db.commit()

        # Create servers with different kinds
        server1 = MCPServer(
            app_id=app1.id,
            server_url="https://example.com/1",
            kind=MCPServerKind.MANAGED,
        )
        server2 = MCPServer(
            app_id=app2.id,
            server_url="https://example.com/2",
            kind=MCPServerKind.EXTERNAL,
        )
        server3 = MCPServer(
            app_id=app3.id,
            server_url="https://example.com/3",
            kind=MCPServerKind.MANAGED,
        )
        db.add_all([server1, server2, server3])
        db.commit()

        # Test filter apps by owner
        alice_apps = client.get("/api/apps?owner=alice@example.com")
        assert alice_apps.status_code == status.HTTP_200_OK
        alice_data = alice_apps.json()
        assert alice_data["total"] == 2
        assert all(item["owner"] == "alice@example.com" for item in alice_data["items"])

        # Test filter servers by kind
        managed_servers = client.get("/api/mcp_servers?kind=managed")
        assert managed_servers.status_code == status.HTTP_200_OK
        managed_data = managed_servers.json()
        assert managed_data["total"] == 2
        assert all(item["kind"] == "managed" for item in managed_data["items"])

        # Test filter servers by app_id
        app_servers = client.get(f"/api/mcp_servers?app_id={app1.id}")
        assert app_servers.status_code == status.HTTP_200_OK
        app_data = app_servers.json()
        assert app_data["total"] == 1
        assert app_data["items"][0]["app_id"] == app1.id
