"""
Dependency injection helpers for FastAPI routes.
"""

from typing import Generator, Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from app.database import get_db
from app.models import App, MCPServer, Tool, Collection, CollectionItem


def get_app_or_404(app_id: int, db: Session = Depends(get_db)) -> App:
    """
    Get an App by ID or raise 404 if not found.

    Args:
        app_id: The app ID to fetch
        db: Database session

    Returns:
        The App instance

    Raises:
        HTTPException: 404 if app not found
    """
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"App with id {app_id} not found",
        )
    return app


def get_mcp_server_or_404(server_id: int, db: Session = Depends(get_db)) -> MCPServer:
    """
    Get an MCPServer by ID or raise 404 if not found.

    Args:
        server_id: The server ID to fetch
        db: Database session

    Returns:
        The MCPServer instance

    Raises:
        HTTPException: 404 if server not found
    """
    server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP Server with id {server_id} not found",
        )
    return server


def get_tool_or_404(tool_id: int, db: Session = Depends(get_db)) -> Tool:
    """
    Get a Tool by ID or raise 404 if not found.

    Args:
        tool_id: The tool ID to fetch
        db: Database session

    Returns:
        The Tool instance

    Raises:
        HTTPException: 404 if tool not found
    """
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with id {tool_id} not found",
        )
    return tool


def get_collection_or_404(collection_id: int, db: Session = Depends(get_db)) -> Collection:
    """
    Get a Collection by ID or raise 404 if not found.

    Args:
        collection_id: The collection ID to fetch
        db: Database session

    Returns:
        The Collection instance

    Raises:
        HTTPException: 404 if collection not found
    """
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection with id {collection_id} not found",
        )
    return collection


def get_collection_item_or_404(item_id: int, db: Session = Depends(get_db)) -> CollectionItem:
    """
    Get a CollectionItem by ID or raise 404 if not found.

    Args:
        item_id: The collection item ID to fetch
        db: Database session

    Returns:
        The CollectionItem instance

    Raises:
        HTTPException: 404 if collection item not found
    """
    item = db.query(CollectionItem).filter(CollectionItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection item with id {item_id} not found",
        )
    return item
