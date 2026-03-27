"""
Tests for Collection and CollectionItem endpoints.
"""

import pytest


def test_list_collections_empty(client):
    """Test listing collections when none exist."""
    response = client.get("/api/collections")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_create_collection(client):
    """Test creating a new collection."""
    response = client.post(
        "/api/collections",
        json={
            "name": "Test Collection",
            "description": "A test collection",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Collection"
    assert "id" in data


def test_create_collection_duplicate_name(client, sample_collection):
    """Test creating collection with duplicate name fails."""
    response = client.post(
        "/api/collections",
        json={
            "name": sample_collection.name,
            "description": "Different description",
        },
    )
    assert response.status_code == 422


def test_get_collection(client, sample_collection):
    """Test getting a specific collection."""
    response = client.get(f"/api/collections/{sample_collection.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_collection.id
    assert data["name"] == sample_collection.name


def test_get_collection_not_found(client):
    """Test getting non-existent collection returns 404."""
    response = client.get("/api/collections/9999")
    assert response.status_code == 404


def test_update_collection(client, sample_collection):
    """Test updating a collection."""
    response = client.put(
        f"/api/collections/{sample_collection.id}",
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


def test_delete_collection(client, sample_collection):
    """Test deleting a collection."""
    response = client.delete(f"/api/collections/{sample_collection.id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/collections/{sample_collection.id}")
    assert response.status_code == 404


# Collection Items tests


def test_list_collection_items_empty(client, sample_collection):
    """Test listing items in an empty collection."""
    response = client.get(f"/api/collections/{sample_collection.id}/items")
    assert response.status_code == 200
    assert response.json() == []


def test_add_app_to_collection(client, sample_collection, sample_app):
    """Test adding an app to a collection."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": sample_app.id,
            "mcp_server_id": None,
            "tool_id": None,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["collection_id"] == sample_collection.id
    assert data["app_id"] == sample_app.id
    assert data["mcp_server_id"] is None
    assert data["tool_id"] is None


def test_add_mcp_server_to_collection(client, sample_collection, sample_mcp_server):
    """Test adding an MCP server to a collection."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": sample_mcp_server.id,
            "tool_id": None,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mcp_server_id"] == sample_mcp_server.id


def test_add_tool_to_collection(client, sample_collection, sample_tool):
    """Test adding a tool to a collection."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": None,
            "tool_id": sample_tool.id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tool_id"] == sample_tool.id


def test_add_item_multiple_refs_fails(client, sample_collection, sample_app, sample_tool):
    """Test adding item with multiple references fails validation."""
    # This should fail at Pydantic validation level
    # Using raise_server_exceptions=False to handle validation errors gracefully
    with pytest.raises(Exception):
        # Pydantic field validator will raise ValueError before route handler
        response = client.post(
            f"/api/collections/{sample_collection.id}/items",
            json={
                "collection_id": sample_collection.id,
                "app_id": sample_app.id,
                "mcp_server_id": None,
                "tool_id": sample_tool.id,
            },
        )


def test_add_item_no_refs_fails(client, sample_collection):
    """Test adding item with no references fails validation."""
    # This should fail at Pydantic validation level
    # Using raise_server_exceptions=False to handle validation errors gracefully
    with pytest.raises(Exception):
        # Pydantic field validator will raise ValueError before route handler
        response = client.post(
            f"/api/collections/{sample_collection.id}/items",
            json={
                "collection_id": sample_collection.id,
                "app_id": None,
                "mcp_server_id": None,
                "tool_id": None,
            },
        )


def test_remove_item_from_collection(client, sample_collection, sample_app, db):
    """Test removing an item from a collection."""
    from app.models import CollectionItem

    # Add item to collection
    item = CollectionItem(
        collection_id=sample_collection.id,
        app_id=sample_app.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Remove item
    response = client.delete(
        f"/api/collections/{sample_collection.id}/items/{item.id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/collections/{sample_collection.id}/items")
    assert response.status_code == 200
    assert response.json() == []


def test_remove_item_from_wrong_collection_fails(client, sample_app, db):
    """Test removing item from wrong collection fails."""
    from app.models import Collection, CollectionItem

    # Create two collections
    collection1 = Collection(name="Collection 1")
    collection2 = Collection(name="Collection 2")
    db.add_all([collection1, collection2])
    db.commit()

    # Add item to collection1
    item = CollectionItem(collection_id=collection1.id, app_id=sample_app.id)
    db.add(item)
    db.commit()
    db.refresh(item)

    # Try to remove from collection2
    response = client.delete(f"/api/collections/{collection2.id}/items/{item.id}")
    assert response.status_code == 404


# Validation tests


def test_add_nonexistent_app_fails(client, sample_collection):
    """Test adding non-existent app to collection fails."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": 9999,
            "mcp_server_id": None,
            "tool_id": None,
        },
    )
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_add_nonexistent_server_fails(client, sample_collection):
    """Test adding non-existent MCP server to collection fails."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": 9999,
            "tool_id": None,
        },
    )
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_add_nonexistent_tool_fails(client, sample_collection):
    """Test adding non-existent tool to collection fails."""
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": None,
            "tool_id": 9999,
        },
    )
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_add_duplicate_app_fails(client, sample_collection, sample_app, db):
    """Test adding duplicate app to collection fails."""
    from app.models import CollectionItem

    # Add app to collection first time
    item = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    db.add(item)
    db.commit()

    # Try to add same app again
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": sample_app.id,
            "mcp_server_id": None,
            "tool_id": None,
        },
    )
    assert response.status_code == 422
    assert "already exists" in response.json()["detail"]


def test_add_duplicate_server_fails(client, sample_collection, sample_mcp_server, db):
    """Test adding duplicate MCP server to collection fails."""
    from app.models import CollectionItem

    # Add server to collection first time
    item = CollectionItem(
        collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    db.add(item)
    db.commit()

    # Try to add same server again
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": sample_mcp_server.id,
            "tool_id": None,
        },
    )
    assert response.status_code == 422
    assert "already exists" in response.json()["detail"]


def test_add_duplicate_tool_fails(client, sample_collection, sample_tool, db):
    """Test adding duplicate tool to collection fails."""
    from app.models import CollectionItem

    # Add tool to collection first time
    item = CollectionItem(collection_id=sample_collection.id, tool_id=sample_tool.id)
    db.add(item)
    db.commit()

    # Try to add same tool again
    response = client.post(
        f"/api/collections/{sample_collection.id}/items",
        json={
            "collection_id": sample_collection.id,
            "app_id": None,
            "mcp_server_id": None,
            "tool_id": sample_tool.id,
        },
    )
    assert response.status_code == 422
    assert "already exists" in response.json()["detail"]


# Pagination and listing tests


def test_list_collections_with_pagination(client, db):
    """Test listing collections with pagination."""
    from app.models import Collection

    # Create multiple collections
    for i in range(5):
        collection = Collection(
            name=f"Collection {i}",
            description=f"Description {i}",
        )
        db.add(collection)
    db.commit()

    # Test pagination
    response = client.get("/api/collections?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


def test_collection_cascade_delete(client, sample_collection, sample_app, db):
    """Test deleting collection cascades to items."""
    from app.models import CollectionItem

    # Add items to collection
    item1 = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    db.add(item1)
    db.commit()

    # Delete collection
    response = client.delete(f"/api/collections/{sample_collection.id}")
    assert response.status_code == 204

    # Verify items are deleted
    items = db.query(CollectionItem).filter(
        CollectionItem.collection_id == sample_collection.id
    ).all()
    assert len(items) == 0


def test_list_items_with_multiple_types(
    client, sample_collection, sample_app, sample_mcp_server, sample_tool, db
):
    """Test listing items shows all types in collection."""
    from app.models import CollectionItem

    # Add different types of items
    item1 = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    item2 = CollectionItem(
        collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    item3 = CollectionItem(collection_id=sample_collection.id, tool_id=sample_tool.id)
    db.add_all([item1, item2, item3])
    db.commit()

    # List items
    response = client.get(f"/api/collections/{sample_collection.id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3

    # Verify item types
    app_items = [i for i in items if i["app_id"] is not None]
    server_items = [i for i in items if i["mcp_server_id"] is not None]
    tool_items = [i for i in items if i["tool_id"] is not None]
    assert len(app_items) == 1
    assert len(server_items) == 1
    assert len(tool_items) == 1


def test_update_collection_name_only(client, sample_collection):
    """Test updating only the collection name."""
    response = client.put(
        f"/api/collections/{sample_collection.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == sample_collection.description


def test_update_collection_description_only(client, sample_collection):
    """Test updating only the collection description."""
    response = client.put(
        f"/api/collections/{sample_collection.id}",
        json={"description": "New description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_collection.name
    assert data["description"] == "New description"


def test_update_collection_duplicate_name_fails(client, sample_collection, db):
    """Test updating collection to duplicate name fails."""
    from app.models import Collection

    # Create another collection
    other_collection = Collection(name="Other Collection")
    db.add(other_collection)
    db.commit()

    # Try to rename to existing name
    response = client.put(
        f"/api/collections/{sample_collection.id}",
        json={"name": other_collection.name},
    )
    assert response.status_code == 422
