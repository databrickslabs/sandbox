"""
Tests for App CRUD endpoints.
"""

import pytest


def test_list_apps_empty(client):
    """Test listing apps when none exist."""
    response = client.get("/api/apps")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


def test_create_app(client):
    """Test creating a new app."""
    response = client.post(
        "/api/apps",
        json={
            "name": "test-app",
            "owner": "test@example.com",
            "url": "https://example.com/app",
            "tags": "test,sample",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-app"
    assert data["owner"] == "test@example.com"
    assert "id" in data


def test_create_app_duplicate_name(client, sample_app):
    """Test creating an app with duplicate name fails."""
    response = client.post(
        "/api/apps",
        json={
            "name": sample_app.name,
            "owner": "another@example.com",
        },
    )
    assert response.status_code == 422


def test_get_app(client, sample_app):
    """Test getting a specific app."""
    response = client.get(f"/api/apps/{sample_app.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_app.id
    assert data["name"] == sample_app.name


def test_get_app_not_found(client):
    """Test getting non-existent app returns 404."""
    response = client.get("/api/apps/9999")
    assert response.status_code == 404


def test_update_app(client, sample_app):
    """Test updating an app."""
    response = client.put(
        f"/api/apps/{sample_app.id}",
        json={"owner": "updated@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["owner"] == "updated@example.com"
    assert data["name"] == sample_app.name  # Unchanged


def test_delete_app(client, sample_app):
    """Test deleting an app."""
    response = client.delete(f"/api/apps/{sample_app.id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/apps/{sample_app.id}")
    assert response.status_code == 404


def test_list_apps_with_pagination(client):
    """Test listing apps with pagination."""
    # Create multiple apps
    for i in range(5):
        client.post(
            "/api/apps",
            json={"name": f"app-{i}", "owner": "test@example.com"},
        )

    # Test pagination
    response = client.get("/api/apps?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3


def test_list_apps_filter_by_owner(client):
    """Test filtering apps by owner."""
    client.post("/api/apps", json={"name": "app-1", "owner": "user1@example.com"})
    client.post("/api/apps", json={"name": "app-2", "owner": "user2@example.com"})

    response = client.get("/api/apps?owner=user1@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["owner"] == "user1@example.com"
