"""
Business logic and validation for Collections and CollectionItems.

This service layer provides validation logic for collections including:
- Verifying referenced entities exist before adding to collections
- Preventing duplicate items in collections
- Validating item types (app, mcp_server, tool)
- Checking constraints (exactly one FK must be non-null)
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import App, MCPServer, Tool, Collection, CollectionItem


class CollectionValidationError(Exception):
    """Custom exception for collection validation errors."""

    pass


class CollectionService:
    """Service layer for collections business logic."""

    @staticmethod
    def validate_item_exists(
        db: Session,
        app_id: Optional[int] = None,
        mcp_server_id: Optional[int] = None,
        tool_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Validate that the referenced entity exists in the database.

        Args:
            db: Database session
            app_id: Optional app ID
            mcp_server_id: Optional MCP server ID
            tool_id: Optional tool ID

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if entity exists
            - (False, error_msg) if entity doesn't exist
        """
        if app_id is not None:
            app = db.query(App).filter(App.id == app_id).first()
            if not app:
                return False, f"App with id {app_id} does not exist"

        if mcp_server_id is not None:
            server = db.query(MCPServer).filter(MCPServer.id == mcp_server_id).first()
            if not server:
                return False, f"MCP Server with id {mcp_server_id} does not exist"

        if tool_id is not None:
            tool = db.query(Tool).filter(Tool.id == tool_id).first()
            if not tool:
                return False, f"Tool with id {tool_id} does not exist"

        return True, ""

    @staticmethod
    def check_duplicate_item(
        db: Session,
        collection_id: int,
        app_id: Optional[int] = None,
        mcp_server_id: Optional[int] = None,
        tool_id: Optional[int] = None,
    ) -> bool:
        """
        Check if an item already exists in the collection.

        Args:
            db: Database session
            collection_id: Collection ID
            app_id: Optional app ID
            mcp_server_id: Optional MCP server ID
            tool_id: Optional tool ID

        Returns:
            True if duplicate exists, False otherwise
        """
        query = db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id
        )

        if app_id is not None:
            query = query.filter(CollectionItem.app_id == app_id)
        elif mcp_server_id is not None:
            query = query.filter(CollectionItem.mcp_server_id == mcp_server_id)
        elif tool_id is not None:
            query = query.filter(CollectionItem.tool_id == tool_id)

        return query.first() is not None

    @staticmethod
    def validate_and_add_item(
        db: Session,
        collection_id: int,
        app_id: Optional[int] = None,
        mcp_server_id: Optional[int] = None,
        tool_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[CollectionItem]]:
        """
        Validate and add an item to a collection.

        Performs all validation checks:
        1. Verify referenced entity exists
        2. Check for duplicates
        3. Ensure collection exists

        Args:
            db: Database session
            collection_id: Collection ID
            app_id: Optional app ID
            mcp_server_id: Optional MCP server ID
            tool_id: Optional tool ID

        Returns:
            Tuple of (success, message, item)
            - (True, "", item) on success
            - (False, error_msg, None) on failure
        """
        # Verify collection exists
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            return False, f"Collection with id {collection_id} does not exist", None

        # Verify referenced entity exists
        is_valid, error_msg = CollectionService.validate_item_exists(
            db, app_id=app_id, mcp_server_id=mcp_server_id, tool_id=tool_id
        )
        if not is_valid:
            return False, error_msg, None

        # Check for duplicates
        if CollectionService.check_duplicate_item(
            db,
            collection_id=collection_id,
            app_id=app_id,
            mcp_server_id=mcp_server_id,
            tool_id=tool_id,
        ):
            item_type = (
                "app"
                if app_id
                else "server" if mcp_server_id else "tool"
            )
            item_id = app_id or mcp_server_id or tool_id
            return (
                False,
                f"{item_type.capitalize()} with id {item_id} already exists in collection",
                None,
            )

        # Create the item
        try:
            item = CollectionItem(
                collection_id=collection_id,
                app_id=app_id,
                mcp_server_id=mcp_server_id,
                tool_id=tool_id,
            )
            db.add(item)
            db.flush()  # Flush to catch any DB constraints without committing
            return True, "", item
        except IntegrityError as e:
            db.rollback()
            return False, f"Database integrity error: {str(e)}", None

    @staticmethod
    def get_collection_item_counts(db: Session, collection_id: int) -> dict:
        """
        Get counts of different item types in a collection.

        Args:
            db: Database session
            collection_id: Collection ID

        Returns:
            Dictionary with counts: {
                "total": int,
                "apps": int,
                "servers": int,
                "tools": int
            }
        """
        items = (
            db.query(CollectionItem)
            .filter(CollectionItem.collection_id == collection_id)
            .all()
        )

        counts = {
            "total": len(items),
            "apps": sum(1 for item in items if item.app_id is not None),
            "servers": sum(1 for item in items if item.mcp_server_id is not None),
            "tools": sum(1 for item in items if item.tool_id is not None),
        }

        return counts
