"""
Tests for CollectionService business logic.
"""

import pytest
from app.services.collections import CollectionService


def test_validate_item_exists_app(db, sample_app):
    """Test validating that an app exists."""
    is_valid, error = CollectionService.validate_item_exists(
        db, app_id=sample_app.id
    )
    assert is_valid
    assert error == ""


def test_validate_item_exists_server(db, sample_mcp_server):
    """Test validating that a server exists."""
    is_valid, error = CollectionService.validate_item_exists(
        db, mcp_server_id=sample_mcp_server.id
    )
    assert is_valid
    assert error == ""


def test_validate_item_exists_tool(db, sample_tool):
    """Test validating that a tool exists."""
    is_valid, error = CollectionService.validate_item_exists(
        db, tool_id=sample_tool.id
    )
    assert is_valid
    assert error == ""


def test_validate_item_nonexistent_app(db):
    """Test validating non-existent app returns error."""
    is_valid, error = CollectionService.validate_item_exists(db, app_id=9999)
    assert not is_valid
    assert "does not exist" in error


def test_validate_item_nonexistent_server(db):
    """Test validating non-existent server returns error."""
    is_valid, error = CollectionService.validate_item_exists(db, mcp_server_id=9999)
    assert not is_valid
    assert "does not exist" in error


def test_validate_item_nonexistent_tool(db):
    """Test validating non-existent tool returns error."""
    is_valid, error = CollectionService.validate_item_exists(db, tool_id=9999)
    assert not is_valid
    assert "does not exist" in error


def test_check_duplicate_item_app(db, sample_collection, sample_app):
    """Test checking for duplicate app in collection."""
    from app.models import CollectionItem

    # No duplicate initially
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, app_id=sample_app.id
    )
    assert not is_duplicate

    # Add item
    item = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    db.add(item)
    db.commit()

    # Now it's a duplicate
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, app_id=sample_app.id
    )
    assert is_duplicate


def test_check_duplicate_item_server(db, sample_collection, sample_mcp_server):
    """Test checking for duplicate server in collection."""
    from app.models import CollectionItem

    # No duplicate initially
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    assert not is_duplicate

    # Add item
    item = CollectionItem(
        collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    db.add(item)
    db.commit()

    # Now it's a duplicate
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    assert is_duplicate


def test_check_duplicate_item_tool(db, sample_collection, sample_tool):
    """Test checking for duplicate tool in collection."""
    from app.models import CollectionItem

    # No duplicate initially
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, tool_id=sample_tool.id
    )
    assert not is_duplicate

    # Add item
    item = CollectionItem(collection_id=sample_collection.id, tool_id=sample_tool.id)
    db.add(item)
    db.commit()

    # Now it's a duplicate
    is_duplicate = CollectionService.check_duplicate_item(
        db, collection_id=sample_collection.id, tool_id=sample_tool.id
    )
    assert is_duplicate


def test_validate_and_add_item_success_app(db, sample_collection, sample_app):
    """Test successfully adding an app to collection."""
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=sample_collection.id, app_id=sample_app.id
    )
    assert success
    assert message == ""
    assert item is not None
    assert item.app_id == sample_app.id


def test_validate_and_add_item_success_server(db, sample_collection, sample_mcp_server):
    """Test successfully adding a server to collection."""
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    assert success
    assert message == ""
    assert item is not None
    assert item.mcp_server_id == sample_mcp_server.id


def test_validate_and_add_item_success_tool(db, sample_collection, sample_tool):
    """Test successfully adding a tool to collection."""
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=sample_collection.id, tool_id=sample_tool.id
    )
    assert success
    assert message == ""
    assert item is not None
    assert item.tool_id == sample_tool.id


def test_validate_and_add_item_nonexistent_collection(db, sample_app):
    """Test adding item to non-existent collection fails."""
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=9999, app_id=sample_app.id
    )
    assert not success
    assert "does not exist" in message
    assert item is None


def test_validate_and_add_item_nonexistent_app(db, sample_collection):
    """Test adding non-existent app fails."""
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=sample_collection.id, app_id=9999
    )
    assert not success
    assert "does not exist" in message
    assert item is None


def test_validate_and_add_item_duplicate_app(db, sample_collection, sample_app):
    """Test adding duplicate app fails."""
    from app.models import CollectionItem

    # Add app first time
    item = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    db.add(item)
    db.commit()

    # Try to add again
    success, message, item = CollectionService.validate_and_add_item(
        db, collection_id=sample_collection.id, app_id=sample_app.id
    )
    assert not success
    assert "already exists" in message
    assert item is None


def test_get_collection_item_counts_empty(db, sample_collection):
    """Test getting counts for empty collection."""
    counts = CollectionService.get_collection_item_counts(db, sample_collection.id)
    assert counts["total"] == 0
    assert counts["apps"] == 0
    assert counts["servers"] == 0
    assert counts["tools"] == 0


def test_get_collection_item_counts_mixed(
    db, sample_collection, sample_app, sample_mcp_server, sample_tool
):
    """Test getting counts for collection with mixed items."""
    from app.models import CollectionItem

    # Add items
    item1 = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    item2 = CollectionItem(
        collection_id=sample_collection.id, mcp_server_id=sample_mcp_server.id
    )
    item3 = CollectionItem(collection_id=sample_collection.id, tool_id=sample_tool.id)
    db.add_all([item1, item2, item3])
    db.commit()

    # Get counts
    counts = CollectionService.get_collection_item_counts(db, sample_collection.id)
    assert counts["total"] == 3
    assert counts["apps"] == 1
    assert counts["servers"] == 1
    assert counts["tools"] == 1


def test_get_collection_item_counts_multiple_same_type(
    db, sample_collection, sample_app
):
    """Test getting counts with multiple items of same type."""
    from app.models import CollectionItem, App

    # Create another app
    app2 = App(name="test-app-2", owner="test@example.com")
    db.add(app2)
    db.commit()

    # Add both apps
    item1 = CollectionItem(collection_id=sample_collection.id, app_id=sample_app.id)
    item2 = CollectionItem(collection_id=sample_collection.id, app_id=app2.id)
    db.add_all([item1, item2])
    db.commit()

    # Get counts
    counts = CollectionService.get_collection_item_counts(db, sample_collection.id)
    assert counts["total"] == 2
    assert counts["apps"] == 2
    assert counts["servers"] == 0
    assert counts["tools"] == 0
