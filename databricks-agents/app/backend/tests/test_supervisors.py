"""
Tests for supervisor generation API endpoints.

Tests the REST API for generating supervisors from collections.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import zipfile
import io

from app.models import Collection, CollectionItem, App, MCPServer, Tool, Supervisor, MCPServerKind


class TestSupervisorGenerate:
    """Test suite for POST /api/supervisors/generate endpoint."""

    def test_generate_supervisor_success(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test generating supervisor from valid collection."""
        response = client.post(
            "/api/supervisors/generate",
            json={
                "collection_id": sample_collection.id,
                "llm_endpoint": "databricks-meta-llama-3-1-70b-instruct",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["collection_id"] == sample_collection.id
        assert data["collection_name"] == sample_collection.name
        assert data["app_name"] == "test-collection"
        assert "files" in data
        assert "supervisor.py" in data["files"]
        assert "requirements.txt" in data["files"]
        assert "app.yaml" in data["files"]
        assert "generated_at" in data

        # Verify supervisor.py contains Pattern 3 elements
        supervisor_code = data["files"]["supervisor.py"]
        assert "fetch_tool_infos" in supervisor_code
        assert "run_supervisor" in supervisor_code

    def test_generate_supervisor_with_tools(
        self, client: TestClient, db: Session
    ):
        """Test generating supervisor from collection with tools."""
        # Create collection with tools
        collection = Collection(name="Tool Collection", description="Test")
        db.add(collection)
        db.commit()

        # Create MCP server and tool
        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        tool = Tool(
            mcp_server_id=mcp_server.id,
            name="test_tool",
            description="Test tool",
            parameters='{"type": "object"}',
        )
        db.add(tool)
        db.commit()

        item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
        db.add(item)
        db.commit()

        response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": collection.id},
        )

        assert response.status_code == 201
        data = response.json()

        # Verify MCP server URL is in generated files
        app_yaml = data["files"]["app.yaml"]
        assert "https://mcp.example.com" in app_yaml

    def test_generate_supervisor_custom_app_name(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test generating supervisor with custom app name."""
        response = client.post(
            "/api/supervisors/generate",
            json={
                "collection_id": sample_collection.id,
                "app_name": "my-custom-supervisor",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["app_name"] == "my-custom-supervisor"

        # Verify app name in app.yaml
        app_yaml = data["files"]["app.yaml"]
        assert "my-custom-supervisor" in app_yaml

    def test_generate_supervisor_custom_llm_endpoint(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test generating supervisor with custom LLM endpoint."""
        response = client.post(
            "/api/supervisors/generate",
            json={
                "collection_id": sample_collection.id,
                "llm_endpoint": "databricks-dbrx-instruct",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify LLM endpoint in app.yaml
        app_yaml = data["files"]["app.yaml"]
        assert "databricks-dbrx-instruct" in app_yaml

    def test_generate_supervisor_collection_not_found(self, client: TestClient):
        """Test generating supervisor with non-existent collection."""
        response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": 9999},
        )

        assert response.status_code == 422
        assert "Collection with id 9999 not found" in response.json()["detail"]

    def test_generate_supervisor_empty_collection(
        self, client: TestClient, db: Session
    ):
        """Test generating supervisor from empty collection."""
        # Create empty collection
        collection = Collection(name="Empty Collection", description="No items")
        db.add(collection)
        db.commit()

        response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": collection.id},
        )

        # Should succeed even with empty collection
        assert response.status_code == 201
        data = response.json()
        assert "files" in data
        assert "supervisor.py" in data["files"]

    def test_generate_supervisor_creates_metadata(
        self, client: TestClient, sample_collection: Collection, db: Session
    ):
        """Test that generating supervisor creates metadata in database."""
        response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id},
        )

        assert response.status_code == 201

        # Verify metadata was created
        supervisor = db.query(Supervisor).filter(
            Supervisor.collection_id == sample_collection.id
        ).first()
        assert supervisor is not None
        assert supervisor.app_name == "test-collection"
        assert supervisor.generated_at is not None

    def test_generate_supervisor_validation_error(self, client: TestClient):
        """Test generating supervisor with invalid request body."""
        response = client.post(
            "/api/supervisors/generate",
            json={},  # Missing required collection_id
        )

        assert response.status_code == 422


class TestSupervisorPreview:
    """Test suite for GET /api/supervisors/{collection_id}/preview endpoint."""

    def test_preview_supervisor_success(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test previewing supervisor generation."""
        response = client.get(
            f"/api/supervisors/{sample_collection.id}/preview"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["collection_id"] == sample_collection.id
        assert data["collection_name"] == sample_collection.name
        assert data["app_name"] == "test-collection"
        assert "mcp_server_urls" in data
        assert "tool_count" in data
        assert "preview" in data
        assert "supervisor.py" in data["preview"]
        assert "requirements.txt" in data["preview"]
        assert "app.yaml" in data["preview"]

        # Verify preview is truncated
        supervisor_preview = data["preview"]["supervisor.py"]
        assert len(supervisor_preview) <= 503  # 500 + "..."

    def test_preview_supervisor_with_tools(
        self, client: TestClient, db: Session
    ):
        """Test previewing supervisor with tools in collection."""
        # Create collection with tools
        collection = Collection(name="Tool Collection", description="Test")
        db.add(collection)
        db.commit()

        # Create MCP server and tool
        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        tool = Tool(
            mcp_server_id=mcp_server.id,
            name="test_tool",
            description="Test tool",
            parameters='{"type": "object"}',
        )
        db.add(tool)
        db.commit()

        item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
        db.add(item)
        db.commit()

        response = client.get(f"/api/supervisors/{collection.id}/preview")

        assert response.status_code == 200
        data = response.json()

        assert data["tool_count"] == 1
        assert "https://mcp.example.com" in data["mcp_server_urls"]

    def test_preview_supervisor_custom_params(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test previewing supervisor with custom parameters."""
        response = client.get(
            f"/api/supervisors/{sample_collection.id}/preview",
            params={
                "llm_endpoint": "databricks-dbrx-instruct",
                "app_name": "custom-name",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "custom-name"

    def test_preview_supervisor_collection_not_found(self, client: TestClient):
        """Test previewing supervisor with non-existent collection."""
        response = client.get("/api/supervisors/9999/preview")

        assert response.status_code == 404
        assert "Collection with id 9999 not found" in response.json()["detail"]

    def test_preview_supervisor_empty_collection(
        self, client: TestClient, db: Session
    ):
        """Test previewing supervisor from empty collection."""
        # Create empty collection
        collection = Collection(name="Empty Collection", description="No items")
        db.add(collection)
        db.commit()

        response = client.get(f"/api/supervisors/{collection.id}/preview")

        assert response.status_code == 200
        data = response.json()
        assert data["tool_count"] == 0
        assert len(data["mcp_server_urls"]) == 0


class TestSupervisorDownload:
    """Test suite for POST /api/supervisors/{collection_id}/download endpoint."""

    def test_download_supervisor_success(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test downloading supervisor as zip file."""
        response = client.post(
            f"/api/supervisors/{sample_collection.id}/download"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert "test-collection.zip" in response.headers["content-disposition"]

        # Verify zip file structure
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, mode="r") as zip_file:
            files = zip_file.namelist()
            assert "supervisor.py" in files
            assert "requirements.txt" in files
            assert "app.yaml" in files

            # Verify content is not empty
            supervisor_content = zip_file.read("supervisor.py").decode("utf-8")
            assert len(supervisor_content) > 0
            assert "fetch_tool_infos" in supervisor_content

    def test_download_supervisor_custom_app_name(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test downloading supervisor with custom app name."""
        response = client.post(
            f"/api/supervisors/{sample_collection.id}/download",
            params={"app_name": "my-custom-app"},
        )

        assert response.status_code == 200
        assert "my-custom-app.zip" in response.headers["content-disposition"]

    def test_download_supervisor_creates_metadata(
        self, client: TestClient, sample_collection: Collection, db: Session
    ):
        """Test that downloading supervisor creates metadata in database."""
        response = client.post(
            f"/api/supervisors/{sample_collection.id}/download"
        )

        assert response.status_code == 200

        # Verify metadata was created
        supervisor = db.query(Supervisor).filter(
            Supervisor.collection_id == sample_collection.id
        ).first()
        assert supervisor is not None
        assert supervisor.app_name == "test-collection"

    def test_download_supervisor_collection_not_found(self, client: TestClient):
        """Test downloading supervisor with non-existent collection."""
        response = client.post("/api/supervisors/9999/download")

        assert response.status_code == 404
        assert "Collection with id 9999 not found" in response.json()["detail"]

    def test_download_supervisor_validation_passes(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test that downloaded supervisor passes validation."""
        response = client.post(
            f"/api/supervisors/{sample_collection.id}/download"
        )

        assert response.status_code == 200

        # If this succeeds, validation passed (generate_and_validate was called)
        # Extract and verify supervisor.py is valid Python
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data, mode="r") as zip_file:
            supervisor_content = zip_file.read("supervisor.py").decode("utf-8")

            # Should be able to compile as Python
            compile(supervisor_content, "<supervisor>", "exec")


class TestSupervisorList:
    """Test suite for GET /api/supervisors endpoint."""

    def test_list_supervisors_empty(self, client: TestClient):
        """Test listing supervisors when none exist."""
        response = client.get("/api/supervisors")

        assert response.status_code == 200
        data = response.json()
        assert data["supervisors"] == []
        assert data["total"] == 0

    def test_list_supervisors_with_data(
        self, client: TestClient, db: Session, sample_collection: Collection
    ):
        """Test listing supervisors after generating some."""
        # Generate two supervisors
        client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id},
        )
        client.post(
            "/api/supervisors/generate",
            json={
                "collection_id": sample_collection.id,
                "app_name": "another-supervisor",
            },
        )

        response = client.get("/api/supervisors")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["supervisors"]) == 2

        # Verify structure of supervisor metadata
        supervisor = data["supervisors"][0]
        assert "id" in supervisor
        assert "collection_id" in supervisor
        assert "app_name" in supervisor
        assert "generated_at" in supervisor
        assert "deployed_url" in supervisor

    def test_list_supervisors_ordered_by_date(
        self, client: TestClient, db: Session, sample_collection: Collection
    ):
        """Test that supervisors are ordered by generation date (newest first)."""
        # Generate two supervisors
        response1 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id, "app_name": "first"},
        )
        response2 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id, "app_name": "second"},
        )

        list_response = client.get("/api/supervisors")

        assert list_response.status_code == 200
        data = list_response.json()

        # Second supervisor should be first (newest)
        assert data["supervisors"][0]["app_name"] == "second"
        assert data["supervisors"][1]["app_name"] == "first"


class TestSupervisorDelete:
    """Test suite for DELETE /api/supervisors/{supervisor_id} endpoint."""

    def test_delete_supervisor_success(
        self, client: TestClient, db: Session, sample_collection: Collection
    ):
        """Test deleting supervisor metadata."""
        # Generate supervisor
        gen_response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id},
        )

        # Get supervisor ID from database
        supervisor = db.query(Supervisor).first()
        assert supervisor is not None

        # Delete supervisor
        response = client.delete(f"/api/supervisors/{supervisor.id}")

        assert response.status_code == 204

        # Verify supervisor was deleted
        supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor.id).first()
        assert supervisor is None

    def test_delete_supervisor_not_found(self, client: TestClient):
        """Test deleting non-existent supervisor."""
        response = client.delete("/api/supervisors/9999")

        assert response.status_code == 404
        assert "Supervisor with id 9999 not found" in response.json()["detail"]


class TestSupervisorIntegration:
    """Integration tests for supervisor generation workflow."""

    def test_full_workflow(
        self, client: TestClient, db: Session
    ):
        """Test complete workflow: preview -> generate -> list -> download -> delete."""
        # Create collection with tools
        collection = Collection(name="Integration Test", description="Test")
        db.add(collection)
        db.commit()

        mcp_server = MCPServer(
            server_url="https://mcp.example.com",
            kind=MCPServerKind.CUSTOM,
        )
        db.add(mcp_server)
        db.commit()

        tool = Tool(
            mcp_server_id=mcp_server.id,
            name="test_tool",
            description="Test",
            parameters='{"type": "object"}',
        )
        db.add(tool)
        db.commit()

        item = CollectionItem(collection_id=collection.id, tool_id=tool.id)
        db.add(item)
        db.commit()

        # Step 1: Preview
        preview_response = client.get(f"/api/supervisors/{collection.id}/preview")
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        assert preview_data["tool_count"] == 1

        # Step 2: Generate
        gen_response = client.post(
            "/api/supervisors/generate",
            json={"collection_id": collection.id},
        )
        assert gen_response.status_code == 201
        gen_data = gen_response.json()
        assert "files" in gen_data

        # Step 3: List
        list_response = client.get("/api/supervisors")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] >= 1

        # Step 4: Download
        download_response = client.post(
            f"/api/supervisors/{collection.id}/download"
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/zip"

        # Step 5: Delete
        supervisor = db.query(Supervisor).first()
        delete_response = client.delete(f"/api/supervisors/{supervisor.id}")
        assert delete_response.status_code == 204

    def test_multiple_collections(
        self, client: TestClient, db: Session
    ):
        """Test generating supervisors from multiple collections."""
        # Create two collections
        collection1 = Collection(name="Collection 1", description="First")
        collection2 = Collection(name="Collection 2", description="Second")
        db.add_all([collection1, collection2])
        db.commit()

        # Generate supervisors from both
        response1 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": collection1.id},
        )
        response2 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": collection2.id},
        )

        assert response1.status_code == 201
        assert response2.status_code == 201

        # List should show both
        list_response = client.get("/api/supervisors")
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 2

    def test_regenerate_supervisor(
        self, client: TestClient, sample_collection: Collection
    ):
        """Test generating supervisor multiple times from same collection."""
        # Generate supervisor twice
        response1 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id},
        )
        response2 = client.post(
            "/api/supervisors/generate",
            json={"collection_id": sample_collection.id},
        )

        assert response1.status_code == 201
        assert response2.status_code == 201

        # Both should succeed and create separate metadata records
        list_response = client.get("/api/supervisors")
        assert list_response.json()["total"] == 2
