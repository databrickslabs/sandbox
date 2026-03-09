"""
Database adapter that switches between SQLite (SQLAlchemy) and Databricks Warehouse.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.config import settings
import app.database as _db_module
from app import models

logger = logging.getLogger(__name__)

USE_SQLITE = settings.database_url.startswith("sqlite")

# Log which backend is active
logger.info(f"[DB-ADAPTER] DATABASE_URL={settings.database_url}")
logger.info(f"[DB-ADAPTER] Using backend: {'SQLite' if USE_SQLITE else 'SQL Warehouse'}")
if not USE_SQLITE:
    logger.info(f"[DB-ADAPTER] Warehouse config: catalog={settings.db_catalog}, schema={settings.db_schema}, warehouse_id={settings.databricks_warehouse_id}")

def safe_timestamp(obj, attr):
    """Safely get timestamp attribute that might not exist."""
    val = getattr(obj, attr, None)
    return val.isoformat() if val else None


class DatabaseAdapter:
    """Adapter that routes to SQLite or Warehouse based on configuration."""

    @staticmethod
    def _get_session() -> Session:
        """Get SQLAlchemy session for SQLite."""
        return _db_module.SessionLocal()

    # ==================== COLLECTIONS ====================

    @staticmethod
    def list_collections(page: int = 1, page_size: int = 50) -> Tuple[List[Dict], int]:
        """List collections with pagination."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                offset = (page - 1) * page_size
                collections = db.query(models.Collection).offset(offset).limit(page_size).all()
                total = db.query(models.Collection).count()

                return (
                    [
                        {
                            "id": c.id,
                            "name": c.name,
                            "description": c.description,
                            "created_at": safe_timestamp(c, 'created_at'),
                            "updated_at": safe_timestamp(c, 'updated_at'),
                        }
                        for c in collections
                    ],
                    total,
                )
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.list_collections(page, page_size)

    @staticmethod
    def get_collection(collection_id: int) -> Optional[Dict]:
        """Get collection by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
                if not collection:
                    return None
                return {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "created_at": safe_timestamp(collection, 'created_at'),
                    "updated_at": safe_timestamp(collection, 'updated_at'),
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.get_collection(collection_id)

    @staticmethod
    def create_collection(name: str, description: str = None) -> Dict:
        """Create new collection."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                collection = models.Collection(name=name, description=description)
                db.add(collection)
                db.commit()
                db.refresh(collection)
                return {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "created_at": safe_timestamp(collection, 'created_at'),
                    "updated_at": safe_timestamp(collection, 'updated_at'),
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.create_collection(name, description)

    @staticmethod
    def update_collection(collection_id: int, **kwargs) -> Optional[Dict]:
        """Update a collection."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
                if not collection:
                    return None
                for key, value in kwargs.items():
                    if value is not None and hasattr(collection, key):
                        setattr(collection, key, value)
                db.commit()
                db.refresh(collection)
                return {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "created_at": safe_timestamp(collection, 'created_at'),
                    "updated_at": safe_timestamp(collection, 'updated_at'),
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.update_collection(collection_id, **kwargs)

    @staticmethod
    def delete_collection(collection_id: int) -> None:
        """Delete a collection."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
                if collection:
                    db.delete(collection)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            WarehouseDB.delete_collection(collection_id)

    # ==================== APPS ====================

    @staticmethod
    def get_app_by_url(url: str) -> Optional[Dict]:
        """Get app by URL."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app = db.query(models.App).filter(models.App.url == url).first()
                if not app:
                    return None
                return {
                    "id": app.id,
                    "name": app.name,
                    "owner": app.owner,
                    "url": app.url,
                    "tags": app.tags,
                    "manifest_url": app.manifest_url,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            apps, _ = WarehouseDB.list_apps(page=1, page_size=1000)
            for app in apps:
                if app.get("url") == url:
                    return app
            return None

    @staticmethod
    def get_app_by_name(name: str) -> Optional[Dict]:
        """Get app by name."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app = db.query(models.App).filter(models.App.name == name).first()
                if not app:
                    return None
                return {
                    "id": app.id,
                    "name": app.name,
                    "owner": app.owner,
                    "url": app.url,
                    "tags": app.tags,
                    "manifest_url": app.manifest_url,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            apps, _ = WarehouseDB.list_apps(page=1, page_size=1000)
            for app in apps:
                if app.get("name") == name:
                    return app
            return None

    @staticmethod
    def upsert_app_by_name(name: str, owner: str = None, url: str = None,
                           tags: str = None, manifest_url: str = None) -> Dict:
        """
        Upsert app by name. Returns app dict with ID.
        If app exists, updates it. If not, creates it.
        """
        existing = DatabaseAdapter.get_app_by_name(name)
        if existing:
            # Update existing app
            update_kwargs = {}
            if owner is not None:
                update_kwargs["owner"] = owner
            if url is not None:
                update_kwargs["url"] = url
            if tags is not None:
                update_kwargs["tags"] = tags
            if manifest_url is not None:
                update_kwargs["manifest_url"] = manifest_url

            if update_kwargs:
                updated = DatabaseAdapter.update_app(existing["id"], **update_kwargs)
                return updated if updated else existing
            return existing
        else:
            # Create new app
            return DatabaseAdapter.create_app(name=name, owner=owner, url=url,
                                            tags=tags, manifest_url=manifest_url)

    @staticmethod
    def create_app(name: str, owner: str = None, url: str = None, tags: str = None, manifest_url: str = None) -> Dict:
        """Create a new app."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app_obj = models.App(name=name, owner=owner, url=url, tags=tags, manifest_url=manifest_url)
                db.add(app_obj)
                db.commit()
                db.refresh(app_obj)
                return {
                    "id": app_obj.id,
                    "name": app_obj.name,
                    "owner": app_obj.owner,
                    "url": app_obj.url,
                    "tags": app_obj.tags,
                    "manifest_url": app_obj.manifest_url,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.create_app(name=name, owner=owner, url=url, tags=tags, manifest_url=manifest_url)

    @staticmethod
    def list_apps(page: int = 1, page_size: int = 50, owner: str = None) -> Tuple[List[Dict], int]:
        """List apps with pagination and optional owner filter."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                offset = (page - 1) * page_size
                query = db.query(models.App)
                if owner:
                    query = query.filter(models.App.owner == owner)
                apps = query.offset(offset).limit(page_size).all()
                total = query.count()

                return (
                    [
                        {
                            "id": a.id,
                            "name": a.name,
                            "owner": a.owner,
                            "url": a.url,
                            "tags": a.tags,
                            "manifest_url": a.manifest_url,
                            "created_at": safe_timestamp(a, 'created_at'),
                            "updated_at": safe_timestamp(a, 'updated_at'),
                        }
                        for a in apps
                    ],
                    total,
                )
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.list_apps(page, page_size)

    @staticmethod
    def update_app(app_id: int, **kwargs) -> Optional[Dict]:
        """Update an app."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app_obj = db.query(models.App).filter(models.App.id == app_id).first()
                if not app_obj:
                    return None
                for key, value in kwargs.items():
                    if value is not None and hasattr(app_obj, key):
                        setattr(app_obj, key, value)
                db.commit()
                db.refresh(app_obj)
                return {
                    "id": app_obj.id,
                    "name": app_obj.name,
                    "owner": app_obj.owner,
                    "url": app_obj.url,
                    "tags": app_obj.tags,
                    "manifest_url": app_obj.manifest_url,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.update_app(app_id, **kwargs)

    @staticmethod
    def delete_app(app_id: int) -> None:
        """Delete an app."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app_obj = db.query(models.App).filter(models.App.id == app_id).first()
                if app_obj:
                    db.delete(app_obj)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            WarehouseDB.delete_app(app_id)

    # ==================== MCP SERVERS ====================

    @staticmethod
    def get_mcp_server_by_url(server_url: str) -> Optional[Dict]:
        """Get MCP server by URL."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                server = db.query(models.MCPServer).filter(
                    models.MCPServer.server_url == server_url
                ).first()
                if not server:
                    return None
                return {
                    "id": server.id,
                    "app_id": server.app_id,
                    "server_url": server.server_url,
                    "kind": server.kind,
                    "uc_connection": server.uc_connection,
                    "scopes": server.scopes,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            servers, _ = WarehouseDB.list_mcp_servers(page=1, page_size=1000, app_id=None)
            for server in servers:
                if server.get("server_url") == server_url:
                    return server
            return None

    @staticmethod
    def upsert_mcp_server_by_url(server_url: str, kind: str = 'managed',
                                 app_id: int = None, uc_connection: str = None,
                                 scopes: str = None) -> Dict:
        """
        Upsert MCP server by URL. Returns server dict with ID.
        If server exists, updates it. If not, creates it.
        """
        existing = DatabaseAdapter.get_mcp_server_by_url(server_url)
        if existing:
            # Update existing server
            update_kwargs = {}
            if kind is not None:
                update_kwargs["kind"] = kind
            if app_id is not None:
                update_kwargs["app_id"] = app_id
            if uc_connection is not None:
                update_kwargs["uc_connection"] = uc_connection
            if scopes is not None:
                update_kwargs["scopes"] = scopes

            if update_kwargs:
                updated = DatabaseAdapter.update_mcp_server(existing["id"], **update_kwargs)
                return updated if updated else existing
            return existing
        else:
            # Create new server
            return DatabaseAdapter.create_mcp_server(
                server_url=server_url, kind=kind, app_id=app_id,
                uc_connection=uc_connection, scopes=scopes
            )

    @staticmethod
    def create_mcp_server(server_url: str, kind: str = 'managed', app_id: int = None, uc_connection: str = None, scopes: str = None) -> Dict:
        """Create a new MCP server."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                server = models.MCPServer(
                    server_url=server_url,
                    kind=kind,
                    app_id=app_id,
                    uc_connection=uc_connection,
                    scopes=scopes,
                )
                db.add(server)
                db.commit()
                db.refresh(server)
                return {
                    "id": server.id,
                    "app_id": server.app_id,
                    "server_url": server.server_url,
                    "kind": server.kind,
                    "uc_connection": server.uc_connection,
                    "scopes": server.scopes,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.create_mcp_server(server_url=server_url, kind=kind, app_id=app_id, uc_connection=uc_connection, scopes=scopes)

    @staticmethod
    def delete_mcp_server(server_id: int) -> None:
        """Delete an MCP server."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
                if server:
                    db.delete(server)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            WarehouseDB.delete_mcp_server(server_id)

    @staticmethod
    def list_mcp_servers(page: int = 1, page_size: int = 50, app_id: int = None, kind: str = None) -> Tuple[List[Dict], int]:
        """List MCP servers with pagination."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                offset = (page - 1) * page_size
                query = db.query(models.MCPServer)
                if app_id:
                    query = query.filter(models.MCPServer.app_id == app_id)
                if kind:
                    query = query.filter(models.MCPServer.kind == kind)
                servers = query.offset(offset).limit(page_size).all()
                total = query.count()

                return (
                    [
                        {
                            "id": s.id,
                            "app_id": s.app_id,
                            "server_url": s.server_url,
                            "kind": s.kind,
                            "uc_connection": s.uc_connection,
                            "scopes": s.scopes,
                            "created_at": safe_timestamp(s, 'created_at'),
                        }
                        for s in servers
                    ],
                    total,
                )
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.list_mcp_servers(page, page_size, app_id)

    @staticmethod
    def update_mcp_server(server_id: int, **kwargs) -> Optional[Dict]:
        """Update an MCP server."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
                if not server:
                    return None
                for key, value in kwargs.items():
                    if value is not None and hasattr(server, key):
                        setattr(server, key, value)
                db.commit()
                db.refresh(server)
                return {
                    "id": server.id,
                    "app_id": server.app_id,
                    "server_url": server.server_url,
                    "kind": server.kind,
                    "uc_connection": server.uc_connection,
                    "scopes": server.scopes,
                    "created_at": safe_timestamp(server, 'created_at'),
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.update_mcp_server(server_id, **kwargs)

    # ==================== TOOLS ====================

    @staticmethod
    def get_tool_by_server_and_name(mcp_server_id: int, name: str) -> Optional[Dict]:
        """Get tool by MCP server ID and tool name."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                tool = db.query(models.Tool).filter(
                    models.Tool.mcp_server_id == mcp_server_id,
                    models.Tool.name == name
                ).first()
                if not tool:
                    return None
                return {
                    "id": tool.id,
                    "mcp_server_id": tool.mcp_server_id,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            tools, _ = WarehouseDB.list_tools(page=1, page_size=1000, mcp_server_id=mcp_server_id)
            for tool in tools:
                if tool.get("name") == name:
                    return tool
            return None

    @staticmethod
    def upsert_tool_by_server_and_name(mcp_server_id: int, name: str,
                                       description: str = None,
                                       parameters: str = None) -> Dict:
        """
        Upsert tool by server ID and name. Returns tool dict with ID.
        If tool exists, updates it. If not, creates it.
        """
        existing = DatabaseAdapter.get_tool_by_server_and_name(mcp_server_id, name)
        if existing:
            # Update existing tool
            update_kwargs = {}
            if description is not None:
                update_kwargs["description"] = description
            if parameters is not None:
                update_kwargs["parameters"] = parameters

            # Note: DatabaseAdapter doesn't have update_tool, so we'd need to add it
            # For now, just return existing if it matches
            return existing
        else:
            # Create new tool
            return DatabaseAdapter.create_tool(
                mcp_server_id=mcp_server_id, name=name,
                description=description, parameters=parameters
            )

    @staticmethod
    def list_tools(page: int = 1, page_size: int = 50, mcp_server_id: int = None,
                   name: str = None, search: str = None, tags: str = None,
                   owner: str = None) -> Tuple[List[Dict], int]:
        """List tools with pagination and filtering."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                offset = (page - 1) * page_size
                query = db.query(models.Tool)
                if mcp_server_id:
                    query = query.filter(models.Tool.mcp_server_id == mcp_server_id)
                if name:
                    query = query.filter(models.Tool.name.ilike(f"%{name}%"))
                if search:
                    pattern = f"%{search}%"
                    query = query.filter(
                        (models.Tool.name.ilike(pattern))
                        | (models.Tool.description.ilike(pattern))
                    )
                # Filter by parent app tags/owner via MCP server join
                if tags or owner:
                    query = query.join(
                        models.MCPServer,
                        models.Tool.mcp_server_id == models.MCPServer.id,
                    ).join(
                        models.App,
                        models.MCPServer.app_id == models.App.id,
                    )
                    if owner:
                        query = query.filter(models.App.owner.ilike(f"%{owner}%"))
                    if tags:
                        tag_list = [t.strip() for t in tags.split(",")]
                        from sqlalchemy import or_
                        tag_filters = [models.App.tags.ilike(f"%{tag}%") for tag in tag_list]
                        query = query.filter(or_(*tag_filters))

                total = query.count()
                tools = query.offset(offset).limit(page_size).all()

                return (
                    [
                        {
                            "id": t.id,
                            "mcp_server_id": t.mcp_server_id,
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                            "created_at": safe_timestamp(t, 'created_at'),
                        }
                        for t in tools
                    ],
                    total,
                )
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.list_tools(page, page_size, mcp_server_id)


    @staticmethod
    def create_tool(mcp_server_id: int, name: str, description: str = None, parameters: str = None) -> Dict:
        """Create a new tool."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                tool = models.Tool(
                    mcp_server_id=mcp_server_id,
                    name=name,
                    description=description,
                    parameters=parameters,
                )
                db.add(tool)
                db.commit()
                db.refresh(tool)
                return {
                    "id": tool.id,
                    "mcp_server_id": tool.mcp_server_id,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.create_tool(mcp_server_id=mcp_server_id, name=name, description=description, parameters=parameters)

    # ==================== COLLECTION ITEMS ====================

    @staticmethod
    def list_collection_items(collection_id: int) -> List[Dict]:
        """List items in a collection."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                items = db.query(models.CollectionItem).filter(
                    models.CollectionItem.collection_id == collection_id
                ).all()

                result = []
                for item in items:
                    item_dict = {
                        "id": item.id,
                        "collection_id": item.collection_id,
                        "app_id": item.app_id,
                        "mcp_server_id": item.mcp_server_id,
                        "tool_id": item.tool_id,
                    }
                    result.append(item_dict)
                return result
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.list_collection_items(collection_id)

    @staticmethod
    def add_collection_item(collection_id: int, app_id: int = None, mcp_server_id: int = None, tool_id: int = None) -> Dict:
        """Add an item to a collection."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                item = models.CollectionItem(
                    collection_id=collection_id,
                    app_id=app_id,
                    mcp_server_id=mcp_server_id,
                    tool_id=tool_id,
                )
                db.add(item)
                db.commit()
                db.refresh(item)
                return {
                    "id": item.id,
                    "collection_id": item.collection_id,
                    "app_id": item.app_id,
                    "mcp_server_id": item.mcp_server_id,
                    "tool_id": item.tool_id,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.add_collection_item(collection_id=collection_id, app_id=app_id, mcp_server_id=mcp_server_id, tool_id=tool_id)

    @staticmethod
    def get_collection_item(item_id: int) -> Optional[Dict]:
        """Get a collection item by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                item = db.query(models.CollectionItem).filter(models.CollectionItem.id == item_id).first()
                if not item:
                    return None
                return {
                    "id": item.id,
                    "collection_id": item.collection_id,
                    "app_id": item.app_id,
                    "mcp_server_id": item.mcp_server_id,
                    "tool_id": item.tool_id,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.get_collection_item(item_id)

    @staticmethod
    def delete_collection_item(item_id: int) -> None:
        """Delete a collection item."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                item = db.query(models.CollectionItem).filter(models.CollectionItem.id == item_id).first()
                if item:
                    db.delete(item)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            WarehouseDB.delete_collection_item(item_id)

    # ==================== INDIVIDUAL LOOKUPS ====================

    @staticmethod
    def get_app(app_id: int) -> Optional[Dict]:
        """Get app by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                app = db.query(models.App).filter(models.App.id == app_id).first()
                if not app:
                    return None
                return {
                    "id": app.id,
                    "name": app.name,
                    "owner": app.owner,
                    "url": app.url,
                    "tags": app.tags,
                    "manifest_url": app.manifest_url,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.get_app(app_id)

    @staticmethod
    def get_mcp_server(server_id: int) -> Optional[Dict]:
        """Get MCP server by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
                if not server:
                    return None
                return {
                    "id": server.id,
                    "app_id": server.app_id,
                    "server_url": server.server_url,
                    "kind": server.kind,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.get_mcp_server(server_id)

    @staticmethod
    def get_tool(tool_id: int) -> Optional[Dict]:
        """Get tool by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                tool = db.query(models.Tool).filter(models.Tool.id == tool_id).first()
                if not tool:
                    return None
                return {
                    "id": tool.id,
                    "mcp_server_id": tool.mcp_server_id,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB
            return WarehouseDB.get_tool(tool_id)

    # ==================== SUPERVISORS ====================

    @staticmethod
    def list_supervisors() -> Tuple[List[Dict], int]:
        """List all generated supervisors."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                supervisors = db.query(models.Supervisor).order_by(models.Supervisor.generated_at.desc()).all()
                return (
                    [
                        {
                            "id": s.id,
                            "collection_id": s.collection_id,
                            "app_name": s.app_name,
                            "generated_at": s.generated_at.isoformat() if s.generated_at else None,
                            "deployed_url": s.deployed_url,
                        }
                        for s in supervisors
                    ],
                    len(supervisors),
                )
            finally:
                db.close()
        else:
            return [], 0

    @staticmethod
    def create_supervisor(collection_id: int, app_name: str, deployed_url: str = None) -> Dict:
        """Create supervisor metadata record."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                from datetime import datetime
                supervisor = models.Supervisor(
                    collection_id=collection_id,
                    app_name=app_name,
                    generated_at=datetime.utcnow(),
                    deployed_url=deployed_url,
                )
                db.add(supervisor)
                db.commit()
                db.refresh(supervisor)
                return {
                    "id": supervisor.id,
                    "collection_id": supervisor.collection_id,
                    "app_name": supervisor.app_name,
                    "generated_at": supervisor.generated_at.isoformat() if supervisor.generated_at else None,
                    "deployed_url": supervisor.deployed_url,
                }
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            return {}

    @staticmethod
    def get_supervisor(supervisor_id: int) -> Optional[Dict]:
        """Get supervisor by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                s = db.query(models.Supervisor).filter(models.Supervisor.id == supervisor_id).first()
                if not s:
                    return None
                return {
                    "id": s.id,
                    "collection_id": s.collection_id,
                    "app_name": s.app_name,
                    "generated_at": s.generated_at.isoformat() if s.generated_at else None,
                    "deployed_url": s.deployed_url,
                }
            finally:
                db.close()
        else:
            return None

    @staticmethod
    def delete_supervisor(supervisor_id: int) -> bool:
        """Delete supervisor metadata. Returns True if found and deleted."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                s = db.query(models.Supervisor).filter(models.Supervisor.id == supervisor_id).first()
                if not s:
                    return False
                db.delete(s)
                db.commit()
                return True
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            return False


    # ==================== AGENTS ====================

    @staticmethod
    def get_agent_by_name(name: str) -> Optional[Dict]:
        """Get agent by name."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agent = db.query(models.Agent).filter(models.Agent.name == name).first()
                if not agent:
                    return None
                return DatabaseAdapter._agent_to_dict(agent)
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            agents, _ = WDB.list_agents(page=1, page_size=1000)
            for agent in agents:
                if agent.get("name") == name:
                    return agent
            return None

    @staticmethod
    def upsert_agent_by_name(name: str, **kwargs) -> Dict:
        """
        Upsert agent by name. Returns agent dict with ID.
        If agent exists, updates factual fields only (preserves manual fields).
        If not, creates new agent with status="discovered".
        """
        existing = DatabaseAdapter.get_agent_by_name(name)
        if existing:
            # Update factual fields only
            update_kwargs = {}
            for key in ["endpoint_url", "description", "capabilities", "a2a_capabilities",
                       "skills", "protocol_version", "app_id"]:
                if key in kwargs and kwargs[key] is not None:
                    update_kwargs[key] = kwargs[key]

            if update_kwargs:
                updated = DatabaseAdapter.update_agent(existing["id"], **update_kwargs)
                return updated if updated else existing
            return existing
        else:
            # Create new agent with discovered status
            create_kwargs = {k: v for k, v in kwargs.items() if v is not None}
            if "status" not in create_kwargs:
                create_kwargs["status"] = "discovered"
            return DatabaseAdapter.create_agent(name=name, **create_kwargs)

    @staticmethod
    def _agent_to_dict(a) -> Dict:
        """Convert Agent ORM object to dict."""
        return {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "capabilities": a.capabilities,
            "status": a.status,
            "collection_id": a.collection_id,
            "endpoint_url": a.endpoint_url,
            "auth_token": a.auth_token,
            "a2a_capabilities": a.a2a_capabilities,
            "skills": a.skills,
            "protocol_version": a.protocol_version,
            "system_prompt": a.system_prompt,
            "created_at": safe_timestamp(a, 'created_at'),
            "updated_at": safe_timestamp(a, 'updated_at'),
        }

    @staticmethod
    def list_agents(page: int = 1, page_size: int = 50) -> Tuple[List[Dict], int]:
        """List agents with pagination."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                offset = (page - 1) * page_size
                agents = db.query(models.Agent).offset(offset).limit(page_size).all()
                total = db.query(models.Agent).count()
                return ([DatabaseAdapter._agent_to_dict(a) for a in agents], total)
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            return WDB.list_agents(page, page_size)

    @staticmethod
    def get_agent(agent_id: int) -> Optional[Dict]:
        """Get agent by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
                if not agent:
                    return None
                return DatabaseAdapter._agent_to_dict(agent)
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            return WDB.get_agent(agent_id)

    @staticmethod
    def create_agent(name: str, description: str = None, capabilities: str = None,
                     status: str = "draft", collection_id: int = None,
                     endpoint_url: str = None, auth_token: str = None,
                     a2a_capabilities: str = None, skills: str = None,
                     protocol_version: str = None, system_prompt: str = None) -> Dict:
        """Create a new agent."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agent = models.Agent(
                    name=name,
                    description=description,
                    capabilities=capabilities,
                    status=status or "draft",
                    collection_id=collection_id,
                    endpoint_url=endpoint_url,
                    auth_token=auth_token,
                    a2a_capabilities=a2a_capabilities,
                    skills=skills,
                    protocol_version=protocol_version,
                    system_prompt=system_prompt,
                )
                db.add(agent)
                db.commit()
                db.refresh(agent)
                return DatabaseAdapter._agent_to_dict(agent)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            return WDB.create_agent(name=name, description=description,
                                    capabilities=capabilities, status=status,
                                    collection_id=collection_id, endpoint_url=endpoint_url)

    @staticmethod
    def update_agent(agent_id: int, **kwargs) -> Optional[Dict]:
        """Update an agent."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
                if not agent:
                    return None
                for key, value in kwargs.items():
                    if value is not None and hasattr(agent, key):
                        setattr(agent, key, value)
                db.commit()
                db.refresh(agent)
                return DatabaseAdapter._agent_to_dict(agent)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            return WDB.update_agent(agent_id, **kwargs)

    @staticmethod
    def delete_agent(agent_id: int) -> None:
        """Delete an agent."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
                if agent:
                    db.delete(agent)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            from app.db_warehouse import WarehouseDB as WDB
            WDB.delete_agent(agent_id)

    @staticmethod
    def list_active_a2a_agents() -> List[Dict]:
        """List agents that are active and have an endpoint_url (A2A-capable)."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                agents = db.query(models.Agent).filter(
                    models.Agent.status == "active",
                    models.Agent.endpoint_url.isnot(None),
                ).all()
                return [DatabaseAdapter._agent_to_dict(a) for a in agents]
            finally:
                db.close()
        else:
            return []

    # ==================== A2A TASKS ====================

    @staticmethod
    def _a2a_task_to_dict(t) -> Dict:
        """Convert A2ATask ORM object to dict."""
        return {
            "id": t.id,
            "agent_id": t.agent_id,
            "context_id": t.context_id,
            "status": t.status,
            "messages": t.messages,
            "artifacts": t.artifacts,
            "metadata_json": t.metadata_json,
            "webhook_url": t.webhook_url,
            "webhook_token": t.webhook_token,
            "created_at": safe_timestamp(t, 'created_at'),
            "updated_at": safe_timestamp(t, 'updated_at'),
        }

    @staticmethod
    def create_a2a_task(task_id: str, agent_id: int, context_id: str = None,
                        status: str = "submitted", messages: str = None,
                        metadata_json: str = None) -> Dict:
        """Create a new A2A task."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                task = models.A2ATask(
                    id=task_id,
                    agent_id=agent_id,
                    context_id=context_id,
                    status=status,
                    messages=messages,
                    metadata_json=metadata_json,
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                return DatabaseAdapter._a2a_task_to_dict(task)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            return {}

    @staticmethod
    def get_a2a_task(task_id: str) -> Optional[Dict]:
        """Get A2A task by ID."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                task = db.query(models.A2ATask).filter(models.A2ATask.id == task_id).first()
                if not task:
                    return None
                return DatabaseAdapter._a2a_task_to_dict(task)
            finally:
                db.close()
        else:
            return None

    @staticmethod
    def update_a2a_task(task_id: str, **kwargs) -> Optional[Dict]:
        """Update an A2A task."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                task = db.query(models.A2ATask).filter(models.A2ATask.id == task_id).first()
                if not task:
                    return None
                for key, value in kwargs.items():
                    if value is not None and hasattr(task, key):
                        setattr(task, key, value)
                db.commit()
                db.refresh(task)
                return DatabaseAdapter._a2a_task_to_dict(task)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()
        else:
            return None

    @staticmethod
    def list_a2a_tasks(agent_id: int = None, context_id: str = None,
                       status: str = None, page: int = 1,
                       page_size: int = 50) -> Tuple[List[Dict], int]:
        """List A2A tasks with optional filters and pagination."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                query = db.query(models.A2ATask)
                if agent_id:
                    query = query.filter(models.A2ATask.agent_id == agent_id)
                if context_id:
                    query = query.filter(models.A2ATask.context_id == context_id)
                if status:
                    query = query.filter(models.A2ATask.status == status)

                total = query.count()
                offset = (page - 1) * page_size
                tasks = query.order_by(models.A2ATask.created_at.desc()).offset(offset).limit(page_size).all()
                return ([DatabaseAdapter._a2a_task_to_dict(t) for t in tasks], total)
            finally:
                db.close()
        else:
            return [], 0

    @staticmethod
    def delete_a2a_task(task_id: str) -> None:
        """Delete an A2A task."""
        if USE_SQLITE:
            db = DatabaseAdapter._get_session()
            try:
                task = db.query(models.A2ATask).filter(models.A2ATask.id == task_id).first()
                if task:
                    db.delete(task)
                    db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    # ==================== CATALOG ASSETS ====================

    @staticmethod
    def _catalog_asset_to_dict(a) -> Dict:
        """Convert CatalogAsset ORM object to dict."""
        return {
            "id": a.id,
            "asset_type": a.asset_type,
            "catalog": a.catalog,
            "schema_name": a.schema_name,
            "name": a.name,
            "full_name": a.full_name,
            "owner": a.owner,
            "comment": a.comment,
            "columns_json": a.columns_json,
            "tags_json": a.tags_json,
            "properties_json": a.properties_json,
            "data_source_format": a.data_source_format,
            "table_type": a.table_type,
            "row_count": a.row_count,
            "created_at": safe_timestamp(a, "created_at"),
            "updated_at": safe_timestamp(a, "updated_at"),
            "last_indexed_at": safe_timestamp(a, "last_indexed_at"),
        }

    @staticmethod
    def list_catalog_assets(
        page: int = 1,
        page_size: int = 50,
        asset_type: str = None,
        catalog: str = None,
        schema_name: str = None,
        search: str = None,
        owner: str = None,
    ) -> Tuple[List[Dict], int]:
        """List catalog assets with optional filters and pagination."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            query = db.query(CatalogAsset)
            if asset_type:
                query = query.filter(CatalogAsset.asset_type == asset_type)
            if catalog:
                query = query.filter(CatalogAsset.catalog == catalog)
            if schema_name:
                query = query.filter(CatalogAsset.schema_name == schema_name)
            if owner:
                query = query.filter(CatalogAsset.owner == owner)
            if search:
                pattern = f"%{search}%"
                query = query.filter(
                    (CatalogAsset.name.ilike(pattern))
                    | (CatalogAsset.comment.ilike(pattern))
                    | (CatalogAsset.full_name.ilike(pattern))
                    | (CatalogAsset.columns_json.ilike(pattern))
                )

            total = query.count()
            offset = (page - 1) * page_size
            assets = query.order_by(CatalogAsset.full_name).offset(offset).limit(page_size).all()
            return ([DatabaseAdapter._catalog_asset_to_dict(a) for a in assets], total)
        finally:
            db.close()

    @staticmethod
    def get_catalog_asset(asset_id: int) -> Optional[Dict]:
        """Get catalog asset by ID."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(CatalogAsset).filter(CatalogAsset.id == asset_id).first()
            if not asset:
                return None
            return DatabaseAdapter._catalog_asset_to_dict(asset)
        finally:
            db.close()

    @staticmethod
    def get_catalog_asset_by_full_name(full_name: str) -> Optional[Dict]:
        """Get catalog asset by three-level namespace."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(CatalogAsset).filter(CatalogAsset.full_name == full_name).first()
            if not asset:
                return None
            return DatabaseAdapter._catalog_asset_to_dict(asset)
        finally:
            db.close()

    @staticmethod
    def create_catalog_asset(**kwargs) -> Dict:
        """Create a new catalog asset."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            # Convert last_indexed_at string to datetime if provided
            if "last_indexed_at" in kwargs and isinstance(kwargs["last_indexed_at"], str):
                from datetime import datetime as dt
                kwargs["last_indexed_at"] = dt.fromisoformat(kwargs["last_indexed_at"].replace("Z", "+00:00"))

            asset = CatalogAsset(**kwargs)
            db.add(asset)
            db.commit()
            db.refresh(asset)
            return DatabaseAdapter._catalog_asset_to_dict(asset)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def update_catalog_asset(asset_id: int, **kwargs) -> Optional[Dict]:
        """Update a catalog asset."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(CatalogAsset).filter(CatalogAsset.id == asset_id).first()
            if not asset:
                return None

            # Convert last_indexed_at string to datetime if provided
            if "last_indexed_at" in kwargs and isinstance(kwargs["last_indexed_at"], str):
                from datetime import datetime as dt
                kwargs["last_indexed_at"] = dt.fromisoformat(kwargs["last_indexed_at"].replace("Z", "+00:00"))

            for key, value in kwargs.items():
                if hasattr(asset, key):
                    setattr(asset, key, value)
            db.commit()
            db.refresh(asset)
            return DatabaseAdapter._catalog_asset_to_dict(asset)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def clear_catalog_assets() -> None:
        """Delete all catalog assets."""
        from app.models.catalog_asset import CatalogAsset

        db = DatabaseAdapter._get_session()
        try:
            db.query(CatalogAsset).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== WORKSPACE ASSETS ====================

    @staticmethod
    def _workspace_asset_to_dict(a) -> Dict:
        """Convert WorkspaceAsset ORM object to dict."""
        return {
            "id": a.id,
            "asset_type": a.asset_type,
            "workspace_host": a.workspace_host,
            "path": a.path,
            "name": a.name,
            "owner": a.owner,
            "description": a.description,
            "language": a.language,
            "tags_json": a.tags_json,
            "metadata_json": a.metadata_json,
            "content_preview": a.content_preview,
            "resource_id": a.resource_id,
            "created_at": safe_timestamp(a, "created_at"),
            "updated_at": safe_timestamp(a, "updated_at"),
            "last_indexed_at": safe_timestamp(a, "last_indexed_at"),
        }

    @staticmethod
    def list_workspace_assets(
        page: int = 1,
        page_size: int = 50,
        asset_type: str = None,
        search: str = None,
        owner: str = None,
        workspace_host: str = None,
    ) -> Tuple[List[Dict], int]:
        """List workspace assets with optional filters and pagination."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            query = db.query(WorkspaceAsset)
            if asset_type:
                query = query.filter(WorkspaceAsset.asset_type == asset_type)
            if workspace_host:
                query = query.filter(WorkspaceAsset.workspace_host == workspace_host)
            if owner:
                query = query.filter(WorkspaceAsset.owner == owner)
            if search:
                pattern = f"%{search}%"
                query = query.filter(
                    (WorkspaceAsset.name.ilike(pattern))
                    | (WorkspaceAsset.description.ilike(pattern))
                    | (WorkspaceAsset.content_preview.ilike(pattern))
                    | (WorkspaceAsset.path.ilike(pattern))
                )

            total = query.count()
            offset = (page - 1) * page_size
            assets = query.order_by(WorkspaceAsset.name).offset(offset).limit(page_size).all()
            return ([DatabaseAdapter._workspace_asset_to_dict(a) for a in assets], total)
        finally:
            db.close()

    @staticmethod
    def get_workspace_asset(asset_id: int) -> Optional[Dict]:
        """Get workspace asset by ID."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(WorkspaceAsset).filter(WorkspaceAsset.id == asset_id).first()
            if not asset:
                return None
            return DatabaseAdapter._workspace_asset_to_dict(asset)
        finally:
            db.close()

    @staticmethod
    def get_workspace_asset_by_path(workspace_host: str, path: str) -> Optional[Dict]:
        """Get workspace asset by host + path."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(WorkspaceAsset).filter(
                WorkspaceAsset.workspace_host == workspace_host,
                WorkspaceAsset.path == path,
            ).first()
            if not asset:
                return None
            return DatabaseAdapter._workspace_asset_to_dict(asset)
        finally:
            db.close()

    @staticmethod
    def create_workspace_asset(**kwargs) -> Dict:
        """Create a new workspace asset."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            if "last_indexed_at" in kwargs and isinstance(kwargs["last_indexed_at"], str):
                from datetime import datetime as dt
                kwargs["last_indexed_at"] = dt.fromisoformat(kwargs["last_indexed_at"].replace("Z", "+00:00"))

            asset = WorkspaceAsset(**kwargs)
            db.add(asset)
            db.commit()
            db.refresh(asset)
            return DatabaseAdapter._workspace_asset_to_dict(asset)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def update_workspace_asset(asset_id: int, **kwargs) -> Optional[Dict]:
        """Update a workspace asset."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            asset = db.query(WorkspaceAsset).filter(WorkspaceAsset.id == asset_id).first()
            if not asset:
                return None

            if "last_indexed_at" in kwargs and isinstance(kwargs["last_indexed_at"], str):
                from datetime import datetime as dt
                kwargs["last_indexed_at"] = dt.fromisoformat(kwargs["last_indexed_at"].replace("Z", "+00:00"))

            for key, value in kwargs.items():
                if hasattr(asset, key):
                    setattr(asset, key, value)
            db.commit()
            db.refresh(asset)
            return DatabaseAdapter._workspace_asset_to_dict(asset)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def clear_workspace_assets() -> None:
        """Delete all workspace assets."""
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            db.query(WorkspaceAsset).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== ASSET EMBEDDINGS ====================

    @staticmethod
    def _embedding_to_dict(e) -> Dict:
        """Convert AssetEmbedding ORM object to dict."""
        return {
            "id": e.id,
            "asset_type": e.asset_type,
            "asset_id": e.asset_id,
            "text_content": e.text_content,
            "embedding_json": e.embedding_json,
            "embedding_model": e.embedding_model,
            "dimension": e.dimension,
            "created_at": safe_timestamp(e, "created_at"),
            "updated_at": safe_timestamp(e, "updated_at"),
        }

    @staticmethod
    def get_asset_embedding(asset_type: str, asset_id: int) -> Optional[Dict]:
        """Get embedding for a specific asset."""
        from app.models.asset_embedding import AssetEmbedding

        db = DatabaseAdapter._get_session()
        try:
            emb = db.query(AssetEmbedding).filter(
                AssetEmbedding.asset_type == asset_type,
                AssetEmbedding.asset_id == asset_id,
            ).first()
            if not emb:
                return None
            return DatabaseAdapter._embedding_to_dict(emb)
        finally:
            db.close()

    @staticmethod
    def create_asset_embedding(**kwargs) -> Dict:
        """Create a new asset embedding."""
        from app.models.asset_embedding import AssetEmbedding

        db = DatabaseAdapter._get_session()
        try:
            emb = AssetEmbedding(**kwargs)
            db.add(emb)
            db.commit()
            db.refresh(emb)
            return DatabaseAdapter._embedding_to_dict(emb)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def update_asset_embedding(embedding_id: int, **kwargs) -> Optional[Dict]:
        """Update an existing embedding."""
        from app.models.asset_embedding import AssetEmbedding

        db = DatabaseAdapter._get_session()
        try:
            emb = db.query(AssetEmbedding).filter(AssetEmbedding.id == embedding_id).first()
            if not emb:
                return None
            for key, value in kwargs.items():
                if hasattr(emb, key):
                    setattr(emb, key, value)
            db.commit()
            db.refresh(emb)
            return DatabaseAdapter._embedding_to_dict(emb)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def list_all_asset_embeddings() -> List[Dict]:
        """List all embeddings (for in-memory similarity search)."""
        from app.models.asset_embedding import AssetEmbedding

        db = DatabaseAdapter._get_session()
        try:
            embeddings = db.query(AssetEmbedding).all()
            return [DatabaseAdapter._embedding_to_dict(e) for e in embeddings]
        finally:
            db.close()

    @staticmethod
    def get_embedding_stats() -> Dict:
        """Get embedding coverage statistics."""
        from app.models.asset_embedding import AssetEmbedding
        from app.models.catalog_asset import CatalogAsset
        from app.models.workspace_asset import WorkspaceAsset

        db = DatabaseAdapter._get_session()
        try:
            embedded_count = db.query(AssetEmbedding).count()
            catalog_count = db.query(CatalogAsset).count()
            workspace_count = db.query(WorkspaceAsset).count()
            app_count = db.query(models.App).count()
            tool_count = db.query(models.Tool).count()
            agent_count = db.query(models.Agent).count()

            total_assets = catalog_count + workspace_count + app_count + tool_count + agent_count

            return {
                "total_assets": total_assets,
                "embedded_assets": embedded_count,
                "pending_assets": max(0, total_assets - embedded_count),
            }
        finally:
            db.close()

    @staticmethod
    def clear_asset_embeddings() -> None:
        """Delete all embeddings."""
        from app.models.asset_embedding import AssetEmbedding

        db = DatabaseAdapter._get_session()
        try:
            db.query(AssetEmbedding).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== ASSET RELATIONSHIPS ====================

    @staticmethod
    def _relationship_to_dict(r) -> Dict:
        """Convert AssetRelationship ORM object to dict."""
        return {
            "id": r.id,
            "source_type": r.source_type,
            "source_id": r.source_id,
            "source_name": r.source_name,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "target_name": r.target_name,
            "relationship_type": r.relationship_type,
            "metadata_json": r.metadata_json,
            "discovered_at": safe_timestamp(r, "discovered_at"),
            "updated_at": safe_timestamp(r, "updated_at"),
        }

    @staticmethod
    def get_asset_relationship(
        source_type: str, source_id: int,
        target_type: str, target_id: int,
        relationship_type: str,
    ) -> Optional[Dict]:
        """Find a specific relationship edge."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            rel = db.query(AssetRelationship).filter(
                AssetRelationship.source_type == source_type,
                AssetRelationship.source_id == source_id,
                AssetRelationship.target_type == target_type,
                AssetRelationship.target_id == target_id,
                AssetRelationship.relationship_type == relationship_type,
            ).first()
            if not rel:
                return None
            return DatabaseAdapter._relationship_to_dict(rel)
        finally:
            db.close()

    @staticmethod
    def create_asset_relationship(**kwargs) -> Dict:
        """Create a new relationship edge."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            rel = AssetRelationship(**kwargs)
            db.add(rel)
            db.commit()
            db.refresh(rel)
            return DatabaseAdapter._relationship_to_dict(rel)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def update_asset_relationship(rel_id: int, **kwargs) -> Optional[Dict]:
        """Update an existing relationship."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            rel = db.query(AssetRelationship).filter(AssetRelationship.id == rel_id).first()
            if not rel:
                return None
            for key, value in kwargs.items():
                if hasattr(rel, key):
                    setattr(rel, key, value)
            db.commit()
            db.refresh(rel)
            return DatabaseAdapter._relationship_to_dict(rel)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get_relationships_by_source(source_type: str, source_id: int) -> List[Dict]:
        """Get all relationships where this asset is the source."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            rels = db.query(AssetRelationship).filter(
                AssetRelationship.source_type == source_type,
                AssetRelationship.source_id == source_id,
            ).all()
            return [DatabaseAdapter._relationship_to_dict(r) for r in rels]
        finally:
            db.close()

    @staticmethod
    def get_relationships_by_target(target_type: str, target_id: int) -> List[Dict]:
        """Get all relationships where this asset is the target."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            rels = db.query(AssetRelationship).filter(
                AssetRelationship.target_type == target_type,
                AssetRelationship.target_id == target_id,
            ).all()
            return [DatabaseAdapter._relationship_to_dict(r) for r in rels]
        finally:
            db.close()

    @staticmethod
    def list_asset_relationships(
        source_type: str = None,
        target_type: str = None,
        relationship_type: str = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Dict], int]:
        """List relationships with optional filters."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            query = db.query(AssetRelationship)
            if source_type:
                query = query.filter(AssetRelationship.source_type == source_type)
            if target_type:
                query = query.filter(AssetRelationship.target_type == target_type)
            if relationship_type:
                query = query.filter(AssetRelationship.relationship_type == relationship_type)

            total = query.count()
            offset = (page - 1) * page_size
            rels = query.order_by(AssetRelationship.discovered_at.desc()).offset(offset).limit(page_size).all()
            return ([DatabaseAdapter._relationship_to_dict(r) for r in rels], total)
        finally:
            db.close()

    @staticmethod
    def clear_asset_relationships() -> None:
        """Delete all relationships."""
        from app.models.asset_relationship import AssetRelationship

        db = DatabaseAdapter._get_session()
        try:
            db.query(AssetRelationship).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ==================== AUDIT LOG ====================

    @staticmethod
    def _audit_log_to_dict(entry) -> Dict:
        """Convert AuditLog ORM object to dict."""
        return {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "user_email": entry.user_email,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "resource_name": entry.resource_name,
            "details": entry.details,
            "ip_address": entry.ip_address,
        }

    @staticmethod
    def create_audit_log(
        user_email: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        resource_name: str = None,
        details: str = None,
        ip_address: str = None,
    ) -> Dict:
        """Create an audit log entry."""
        from app.models.audit_log import AuditLog

        db = DatabaseAdapter._get_session()
        try:
            entry = AuditLog(
                user_email=user_email,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                details=details,
                ip_address=ip_address,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return DatabaseAdapter._audit_log_to_dict(entry)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def list_audit_logs(
        page: int = 1,
        page_size: int = 50,
        user_email: str = None,
        action: str = None,
        resource_type: str = None,
        date_from: str = None,
        date_to: str = None,
    ) -> Tuple[List[Dict], int]:
        """List audit log entries with optional filters and pagination."""
        from app.models.audit_log import AuditLog

        db = DatabaseAdapter._get_session()
        try:
            query = db.query(AuditLog)
            if user_email:
                query = query.filter(AuditLog.user_email == user_email)
            if action:
                query = query.filter(AuditLog.action == action)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            if date_from:
                from datetime import datetime as dt
                query = query.filter(AuditLog.timestamp >= dt.fromisoformat(date_from))
            if date_to:
                from datetime import datetime as dt
                query = query.filter(AuditLog.timestamp <= dt.fromisoformat(date_to))

            total = query.count()
            offset = (page - 1) * page_size
            entries = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
            return ([DatabaseAdapter._audit_log_to_dict(e) for e in entries], total)
        finally:
            db.close()


    # ==================== CONVERSATIONS ====================

    @staticmethod
    def _conversation_to_dict(c) -> Dict:
        """Convert Conversation ORM object to dict."""
        return {
            "id": c.id,
            "title": c.title,
            "user_email": c.user_email,
            "collection_id": c.collection_id,
            "created_at": safe_timestamp(c, "created_at"),
            "updated_at": safe_timestamp(c, "updated_at"),
        }

    @staticmethod
    def _conversation_message_to_dict(m) -> Dict:
        """Convert ConversationMessage ORM object to dict."""
        return {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "trace_id": m.trace_id,
            "created_at": safe_timestamp(m, "created_at"),
        }

    @staticmethod
    def create_conversation(id: str, title: str, user_email: str = None,
                            collection_id: int = None) -> Dict:
        """Create a new conversation."""
        from app.models.conversation import Conversation

        db = DatabaseAdapter._get_session()
        try:
            conv = Conversation(
                id=id,
                title=title,
                user_email=user_email,
                collection_id=collection_id,
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            return DatabaseAdapter._conversation_to_dict(conv)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get_conversation(conversation_id: str) -> Optional[Dict]:
        """Get conversation with its messages."""
        from app.models.conversation import Conversation, ConversationMessage

        db = DatabaseAdapter._get_session()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                return None

            messages = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at)
                .all()
            )

            result = DatabaseAdapter._conversation_to_dict(conv)
            result["messages"] = [DatabaseAdapter._conversation_message_to_dict(m) for m in messages]
            result["message_count"] = len(messages)
            return result
        finally:
            db.close()

    @staticmethod
    def list_conversations(user_email: str = None, page: int = 1,
                           page_size: int = 50) -> Tuple[List[Dict], int]:
        """List conversations, newest first."""
        from app.models.conversation import Conversation, ConversationMessage
        from sqlalchemy import func

        db = DatabaseAdapter._get_session()
        try:
            query = db.query(Conversation)
            if user_email:
                query = query.filter(Conversation.user_email == user_email)

            total = query.count()
            offset = (page - 1) * page_size
            convs = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(page_size).all()

            results = []
            for conv in convs:
                d = DatabaseAdapter._conversation_to_dict(conv)
                d["message_count"] = (
                    db.query(func.count(ConversationMessage.id))
                    .filter(ConversationMessage.conversation_id == conv.id)
                    .scalar()
                )
                results.append(d)

            return results, total
        finally:
            db.close()

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and its messages. Returns True if found."""
        from app.models.conversation import Conversation, ConversationMessage

        db = DatabaseAdapter._get_session()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                return False
            db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).delete()
            db.delete(conv)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def update_conversation_title(conversation_id: str, title: str) -> Optional[Dict]:
        """Rename a conversation."""
        from app.models.conversation import Conversation

        db = DatabaseAdapter._get_session()
        try:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                return None
            conv.title = title
            db.commit()
            db.refresh(conv)
            return DatabaseAdapter._conversation_to_dict(conv)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def create_conversation_message(conversation_id: str, role: str,
                                     content: str, trace_id: str = None) -> Dict:
        """Add a message to a conversation and touch the conversation's updated_at."""
        from app.models.conversation import Conversation, ConversationMessage
        from datetime import datetime

        db = DatabaseAdapter._get_session()
        try:
            msg = ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                trace_id=trace_id,
            )
            db.add(msg)

            # Touch conversation updated_at
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                conv.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(msg)
            return DatabaseAdapter._conversation_message_to_dict(msg)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


    # ==================== AGENT ANALYTICS ====================

    @staticmethod
    def _agent_analytic_to_dict(a) -> Dict:
        """Convert AgentAnalytics ORM object to dict."""
        return {
            "id": a.id,
            "agent_id": a.agent_id,
            "task_description": a.task_description,
            "success": a.success,
            "latency_ms": a.latency_ms,
            "quality_score": a.quality_score,
            "error_message": a.error_message,
            "created_at": safe_timestamp(a, "created_at"),
        }

    @staticmethod
    def create_agent_analytic(
        agent_id: int,
        task_description: str = None,
        success: int = 1,
        latency_ms: int = None,
        quality_score: int = None,
        error_message: str = None,
    ) -> Dict:
        """Record an analytics entry for an agent invocation."""
        from app.models.agent_analytics import AgentAnalytics

        db = DatabaseAdapter._get_session()
        try:
            entry = AgentAnalytics(
                agent_id=agent_id,
                task_description=task_description,
                success=success,
                latency_ms=latency_ms,
                quality_score=quality_score,
                error_message=error_message,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return DatabaseAdapter._agent_analytic_to_dict(entry)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def list_agent_analytics(agent_id: int, limit: int = 50) -> List[Dict]:
        """List recent analytics for a specific agent."""
        from app.models.agent_analytics import AgentAnalytics

        db = DatabaseAdapter._get_session()
        try:
            entries = (
                db.query(AgentAnalytics)
                .filter(AgentAnalytics.agent_id == agent_id)
                .order_by(AgentAnalytics.created_at.desc())
                .limit(limit)
                .all()
            )
            return [DatabaseAdapter._agent_analytic_to_dict(e) for e in entries]
        finally:
            db.close()

    @staticmethod
    def get_agent_summary_stats(agent_id: int) -> Dict:
        """Get aggregated stats for a specific agent."""
        from app.models.agent_analytics import AgentAnalytics
        from sqlalchemy import func

        db = DatabaseAdapter._get_session()
        try:
            total = db.query(func.count(AgentAnalytics.id)).filter(
                AgentAnalytics.agent_id == agent_id
            ).scalar() or 0

            successes = db.query(func.count(AgentAnalytics.id)).filter(
                AgentAnalytics.agent_id == agent_id,
                AgentAnalytics.success == 1,
            ).scalar() or 0

            avg_latency = db.query(func.avg(AgentAnalytics.latency_ms)).filter(
                AgentAnalytics.agent_id == agent_id,
                AgentAnalytics.latency_ms.isnot(None),
            ).scalar()

            avg_quality = db.query(func.avg(AgentAnalytics.quality_score)).filter(
                AgentAnalytics.agent_id == agent_id,
                AgentAnalytics.quality_score.isnot(None),
            ).scalar()

            return {
                "agent_id": agent_id,
                "total_invocations": total,
                "success_count": successes,
                "failure_count": total - successes,
                "success_rate": round(successes / total, 4) if total > 0 else None,
                "avg_latency_ms": round(avg_latency) if avg_latency is not None else None,
                "avg_quality_score": round(float(avg_quality), 2) if avg_quality is not None else None,
            }
        finally:
            db.close()


# Alias for backward compatibility
WarehouseDB = DatabaseAdapter
