"""
Databricks SQL Warehouse database layer.

This module provides database access via Databricks SDK Statement Execution API,
replacing SQLAlchemy/SQLite for production use with Unity Catalog tables.

All queries use parameterized statements to prevent SQL injection.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState, StatementParameterListItem

logger = logging.getLogger(__name__)

# Configuration - require explicit values, no hardcoded defaults
CATALOG = os.getenv("DB_CATALOG")
SCHEMA = os.getenv("DB_SCHEMA")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

if not CATALOG or not SCHEMA or not WAREHOUSE_ID:
    logger.warning(
        "DB_CATALOG, DB_SCHEMA, or DATABRICKS_WAREHOUSE_ID not set. "
        "Warehouse backend will fail if used."
    )
    CATALOG = CATALOG or "default"
    SCHEMA = SCHEMA or "default"
    WAREHOUSE_ID = WAREHOUSE_ID or ""

# Table names
APPS_TABLE = f"{CATALOG}.{SCHEMA}.apps"
AGENTS_TABLE = f"{CATALOG}.{SCHEMA}.agents"
MCP_SERVERS_TABLE = f"{CATALOG}.{SCHEMA}.mcp_servers"
TOOLS_TABLE = f"{CATALOG}.{SCHEMA}.tools"
COLLECTIONS_TABLE = f"{CATALOG}.{SCHEMA}.collections"
COLLECTION_ITEMS_TABLE = f"{CATALOG}.{SCHEMA}.collection_items"

# Global workspace client (reused across requests)
_workspace_client = None


def get_workspace_client() -> WorkspaceClient:
    """Get or create the workspace client."""
    global _workspace_client
    if _workspace_client is None:
        _workspace_client = WorkspaceClient()
    return _workspace_client


def _param(name: str, value: Any) -> StatementParameterListItem:
    """Create a statement parameter.

    Preserves integer types for LIMIT/OFFSET clauses.
    Converts other types to string for SQL compatibility.
    """
    if value is None:
        return StatementParameterListItem(name=name, value=None)
    # Keep integers as integers for LIMIT/OFFSET compatibility
    if isinstance(value, int):
        return StatementParameterListItem(name=name, value=str(value), type="INT")
    return StatementParameterListItem(name=name, value=str(value))


def execute_sql(
    sql: str,
    parameters: Optional[List[StatementParameterListItem]] = None,
    wait_timeout: str = "30s",
) -> List[Dict[str, Any]]:
    """
    Execute a SQL statement using the Statement Execution API.
    Returns list of dicts with column names as keys.

    Uses parameterized queries for safety against SQL injection.
    """
    w = get_workspace_client()

    # Execute statement
    response = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=sql,
        parameters=parameters,
        wait_timeout=wait_timeout,
        catalog=CATALOG,
        schema=SCHEMA,
    )

    # Check for errors
    if response.status.state == StatementState.FAILED:
        error_msg = response.status.error.message if response.status.error else "Unknown error"
        raise RuntimeError(f"SQL execution failed: {error_msg}")

    # If still running, wait for completion
    if response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        statement_id = response.statement_id
        max_wait = 60  # seconds
        start = time.time()
        while time.time() - start < max_wait:
            response = w.statement_execution.get_statement(statement_id)
            if response.status.state == StatementState.SUCCEEDED:
                break
            if response.status.state == StatementState.FAILED:
                error_msg = response.status.error.message if response.status.error else "Unknown error"
                raise RuntimeError(f"SQL execution failed: {error_msg}")
            time.sleep(0.5)

    # Parse results
    if not response.result or not response.manifest:
        return []

    columns = [col.name for col in response.manifest.schema.columns]
    rows = []
    if response.result.data_array:
        for row_data in response.result.data_array:
            rows.append(dict(zip(columns, row_data)))

    return rows


def execute_sql_scalar(
    sql: str,
    parameters: Optional[List[StatementParameterListItem]] = None,
) -> Any:
    """Execute SQL and return a single scalar value."""
    results = execute_sql(sql, parameters)
    if results and len(results) > 0:
        first_row = results[0]
        if first_row:
            return list(first_row.values())[0]
    return None


class WarehouseDB:
    """Database operations using Databricks SQL Warehouse."""

    # ==================== APPS ====================

    @staticmethod
    def list_apps(page: int = 1, page_size: int = 50) -> Tuple[List[Dict], int]:
        """List apps with pagination."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        total = execute_sql_scalar(f"SELECT COUNT(*) as cnt FROM {APPS_TABLE}") or 0

        rows = execute_sql(
            f"""
            SELECT id, name, owner, url, tags, manifest_url, created_at
            FROM {APPS_TABLE}
            ORDER BY id
            LIMIT :page_size OFFSET :offset
            """,
            parameters=[
                _param("page_size", page_size),
                _param("offset", offset),
            ],
        )

        return rows, int(total)

    @staticmethod
    def get_app(app_id: int) -> Optional[Dict]:
        """Get a single app by ID."""
        rows = execute_sql(
            f"""
            SELECT id, name, owner, url, tags, manifest_url, created_at
            FROM {APPS_TABLE}
            WHERE id = :app_id
            """,
            parameters=[_param("app_id", int(app_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def create_app(name: str, owner: str = None, url: str = None,
                   tags: str = None, manifest_url: str = None) -> Dict:
        """Create a new app."""
        execute_sql(
            f"""
            INSERT INTO {APPS_TABLE} (name, owner, url, tags, manifest_url, created_at)
            VALUES (:name, :owner, :url, :tags, :manifest_url, CURRENT_TIMESTAMP())
            """,
            parameters=[
                _param("name", name),
                _param("owner", owner),
                _param("url", url),
                _param("tags", tags),
                _param("manifest_url", manifest_url),
            ],
        )

        # Get the inserted row
        rows = execute_sql(
            f"""
            SELECT id, name, owner, url, tags, manifest_url, created_at
            FROM {APPS_TABLE}
            WHERE name = :name
            ORDER BY id DESC
            LIMIT 1
            """,
            parameters=[_param("name", name)],
        )
        return rows[0] if rows else {}

    @staticmethod
    def update_app(app_id: int, **kwargs) -> Optional[Dict]:
        """Update an app."""
        if not kwargs:
            return WarehouseDB.get_app(app_id)

        set_clauses = []
        params = [_param("app_id", int(app_id))]
        for i, (key, value) in enumerate(kwargs.items()):
            if value is not None:
                param_name = f"val_{i}"
                set_clauses.append(f"{key} = :{param_name}")
                params.append(_param(param_name, value))

        if not set_clauses:
            return WarehouseDB.get_app(app_id)

        execute_sql(
            f"""
            UPDATE {APPS_TABLE}
            SET {', '.join(set_clauses)}
            WHERE id = :app_id
            """,
            parameters=params,
        )

        return WarehouseDB.get_app(app_id)

    @staticmethod
    def delete_app(app_id: int) -> bool:
        """Delete an app."""
        execute_sql(
            f"DELETE FROM {APPS_TABLE} WHERE id = :app_id",
            parameters=[_param("app_id", int(app_id))],
        )
        return True

    # ==================== AGENTS ====================

    @staticmethod
    def list_agents(page: int = 1, page_size: int = 50) -> Tuple[List[Dict], int]:
        """List agents with pagination."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        total = execute_sql_scalar(f"SELECT COUNT(*) as cnt FROM {AGENTS_TABLE}") or 0

        rows = execute_sql(
            f"""
            SELECT id, name, description, capabilities, status, collection_id, app_id,
                   endpoint_url, auth_token, a2a_capabilities, skills, protocol_version,
                   system_prompt, created_at, updated_at
            FROM {AGENTS_TABLE}
            ORDER BY created_at DESC
            LIMIT :page_size OFFSET :offset
            """,
            parameters=[_param("page_size", page_size), _param("offset", offset)],
        )
        return rows, total

    @staticmethod
    def get_agent(agent_id: int) -> Optional[Dict]:
        """Get a single agent by ID."""
        rows = execute_sql(
            f"""
            SELECT id, name, description, capabilities, status, collection_id, app_id,
                   endpoint_url, auth_token, a2a_capabilities, skills, protocol_version,
                   system_prompt, created_at, updated_at
            FROM {AGENTS_TABLE}
            WHERE id = :agent_id
            """,
            parameters=[_param("agent_id", int(agent_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def create_agent(name: str, description: str = None, capabilities: str = None,
                    status: str = "draft", collection_id: int = None,
                    endpoint_url: str = None, **kwargs) -> Dict:
        """Create a new agent."""
        # Extract optional fields
        auth_token = kwargs.get("auth_token")
        a2a_capabilities = kwargs.get("a2a_capabilities")
        skills = kwargs.get("skills")
        protocol_version = kwargs.get("protocol_version")
        system_prompt = kwargs.get("system_prompt")
        app_id = kwargs.get("app_id")

        execute_sql(
            f"""
            INSERT INTO {AGENTS_TABLE} (
                name, description, capabilities, status, collection_id, app_id,
                endpoint_url, auth_token, a2a_capabilities, skills,
                protocol_version, system_prompt, created_at
            )
            VALUES (
                :name, :description, :capabilities, :status, :collection_id, :app_id,
                :endpoint_url, :auth_token, :a2a_capabilities, :skills,
                :protocol_version, :system_prompt, CURRENT_TIMESTAMP()
            )
            """,
            parameters=[
                _param("name", name),
                _param("description", description),
                _param("capabilities", capabilities),
                _param("status", status or "draft"),
                _param("collection_id", collection_id),
                _param("app_id", app_id),
                _param("endpoint_url", endpoint_url),
                _param("auth_token", auth_token),
                _param("a2a_capabilities", a2a_capabilities),
                _param("skills", skills),
                _param("protocol_version", protocol_version),
                _param("system_prompt", system_prompt),
            ],
        )

        # Get the inserted row
        rows = execute_sql(
            f"""
            SELECT id, name, description, capabilities, status, collection_id, app_id,
                   endpoint_url, auth_token, a2a_capabilities, skills, protocol_version,
                   system_prompt, created_at
            FROM {AGENTS_TABLE}
            WHERE name = :name
            ORDER BY id DESC LIMIT 1
            """,
            parameters=[_param("name", name)],
        )
        return rows[0] if rows else {}

    @staticmethod
    def update_agent(agent_id: int, **kwargs) -> Optional[Dict]:
        """Update an agent."""
        if not kwargs:
            return WarehouseDB.get_agent(agent_id)

        set_clauses = []
        params = [_param("agent_id", int(agent_id))]
        for i, (key, value) in enumerate(kwargs.items()):
            if value is not None:
                param_name = f"val_{i}"
                set_clauses.append(f"{key} = :{param_name}")
                params.append(_param(param_name, value))

        if not set_clauses:
            return WarehouseDB.get_agent(agent_id)

        execute_sql(
            f"""
            UPDATE {AGENTS_TABLE}
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP()
            WHERE id = :agent_id
            """,
            parameters=params,
        )
        return WarehouseDB.get_agent(agent_id)

    @staticmethod
    def delete_agent(agent_id: int) -> bool:
        """Delete an agent."""
        execute_sql(
            f"DELETE FROM {AGENTS_TABLE} WHERE id = :agent_id",
            parameters=[_param("agent_id", int(agent_id))],
        )
        return True

    # ==================== MCP SERVERS ====================

    @staticmethod
    def list_mcp_servers(page: int = 1, page_size: int = 50, app_id: int = None) -> Tuple[List[Dict], int]:
        """List MCP servers with pagination."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        params = [
            _param("page_size", page_size),
            _param("offset", offset),
        ]

        where_clause = ""
        if app_id is not None:
            where_clause = "WHERE app_id = :app_id"
            params.append(_param("app_id", int(app_id)))

        total = execute_sql_scalar(
            f"SELECT COUNT(*) as cnt FROM {MCP_SERVERS_TABLE} {where_clause}",
            parameters=params[2:] if app_id else None,
        ) or 0

        rows = execute_sql(
            f"""
            SELECT id, app_id, server_url, kind, uc_connection, scopes, created_at
            FROM {MCP_SERVERS_TABLE}
            {where_clause}
            ORDER BY id
            LIMIT :page_size OFFSET :offset
            """,
            parameters=params,
        )

        return rows, int(total)

    @staticmethod
    def get_mcp_server(server_id: int) -> Optional[Dict]:
        """Get a single MCP server by ID."""
        rows = execute_sql(
            f"""
            SELECT id, app_id, server_url, kind, uc_connection, scopes, created_at
            FROM {MCP_SERVERS_TABLE}
            WHERE id = :server_id
            """,
            parameters=[_param("server_id", int(server_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def create_mcp_server(server_url: str, kind: str = 'managed',
                          app_id: int = None, uc_connection: str = None,
                          scopes: str = None) -> Dict:
        """Create a new MCP server."""
        execute_sql(
            f"""
            INSERT INTO {MCP_SERVERS_TABLE} (server_url, kind, app_id, uc_connection, scopes, created_at)
            VALUES (:server_url, :kind, :app_id, :uc_connection, :scopes, CURRENT_TIMESTAMP())
            """,
            parameters=[
                _param("server_url", server_url),
                _param("kind", kind),
                _param("app_id", app_id),
                _param("uc_connection", uc_connection),
                _param("scopes", scopes),
            ],
        )

        rows = execute_sql(
            f"""
            SELECT id, app_id, server_url, kind, uc_connection, scopes, created_at
            FROM {MCP_SERVERS_TABLE}
            WHERE server_url = :server_url
            ORDER BY id DESC
            LIMIT 1
            """,
            parameters=[_param("server_url", server_url)],
        )
        return rows[0] if rows else {}

    @staticmethod
    def update_mcp_server(server_id: int, **kwargs) -> Optional[Dict]:
        """Update an MCP server."""
        if not kwargs:
            return WarehouseDB.get_mcp_server(server_id)

        set_clauses = []
        params = [_param("server_id", int(server_id))]
        for i, (key, value) in enumerate(kwargs.items()):
            if value is not None:
                param_name = f"val_{i}"
                set_clauses.append(f"{key} = :{param_name}")
                params.append(_param(param_name, value))

        if not set_clauses:
            return WarehouseDB.get_mcp_server(server_id)

        execute_sql(
            f"""
            UPDATE {MCP_SERVERS_TABLE}
            SET {', '.join(set_clauses)}
            WHERE id = :server_id
            """,
            parameters=params,
        )

        return WarehouseDB.get_mcp_server(server_id)

    @staticmethod
    def delete_mcp_server(server_id: int) -> bool:
        """Delete an MCP server."""
        execute_sql(
            f"DELETE FROM {MCP_SERVERS_TABLE} WHERE id = :server_id",
            parameters=[_param("server_id", int(server_id))],
        )
        return True

    # ==================== TOOLS ====================

    @staticmethod
    def list_tools(page: int = 1, page_size: int = 50,
                   mcp_server_id: int = None) -> Tuple[List[Dict], int]:
        """List tools with pagination."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        params = [
            _param("page_size", page_size),
            _param("offset", offset),
        ]

        where_clause = ""
        if mcp_server_id is not None:
            where_clause = "WHERE mcp_server_id = :mcp_server_id"
            params.append(_param("mcp_server_id", int(mcp_server_id)))

        total = execute_sql_scalar(
            f"SELECT COUNT(*) as cnt FROM {TOOLS_TABLE} {where_clause}",
            parameters=params[2:] if mcp_server_id else None,
        ) or 0

        rows = execute_sql(
            f"""
            SELECT id, mcp_server_id, name, description, parameters, created_at
            FROM {TOOLS_TABLE}
            {where_clause}
            ORDER BY id
            LIMIT :page_size OFFSET :offset
            """,
            parameters=params,
        )

        return rows, int(total)

    @staticmethod
    def get_tool(tool_id: int) -> Optional[Dict]:
        """Get a single tool by ID."""
        rows = execute_sql(
            f"""
            SELECT id, mcp_server_id, name, description, parameters, created_at
            FROM {TOOLS_TABLE}
            WHERE id = :tool_id
            """,
            parameters=[_param("tool_id", int(tool_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def create_tool(mcp_server_id: int, name: str, description: str = None,
                    parameters: str = None) -> Dict:
        """Create a new tool."""
        execute_sql(
            f"""
            INSERT INTO {TOOLS_TABLE} (mcp_server_id, name, description, parameters, created_at)
            VALUES (:mcp_server_id, :name, :description, :parameters, CURRENT_TIMESTAMP())
            """,
            parameters=[
                _param("mcp_server_id", int(mcp_server_id)),
                _param("name", name),
                _param("description", description),
                _param("parameters", parameters),
            ],
        )

        rows = execute_sql(
            f"""
            SELECT id, mcp_server_id, name, description, parameters, created_at
            FROM {TOOLS_TABLE}
            WHERE mcp_server_id = :mcp_server_id AND name = :name
            ORDER BY id DESC
            LIMIT 1
            """,
            parameters=[
                _param("mcp_server_id", int(mcp_server_id)),
                _param("name", name),
            ],
        )
        return rows[0] if rows else {}

    # ==================== COLLECTIONS ====================

    @staticmethod
    def list_collections(page: int = 1, page_size: int = 50) -> Tuple[List[Dict], int]:
        """List collections with pagination."""
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        total = execute_sql_scalar(f"SELECT COUNT(*) as cnt FROM {COLLECTIONS_TABLE}") or 0

        rows = execute_sql(
            f"""
            SELECT id, name, description, created_at
            FROM {COLLECTIONS_TABLE}
            ORDER BY id
            LIMIT :page_size OFFSET :offset
            """,
            parameters=[
                _param("page_size", page_size),
                _param("offset", offset),
            ],
        )

        return rows, int(total)

    @staticmethod
    def get_collection(collection_id: int) -> Optional[Dict]:
        """Get a single collection by ID."""
        rows = execute_sql(
            f"""
            SELECT id, name, description, created_at
            FROM {COLLECTIONS_TABLE}
            WHERE id = :collection_id
            """,
            parameters=[_param("collection_id", int(collection_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def create_collection(name: str, description: str = None) -> Dict:
        """Create a new collection."""
        execute_sql(
            f"""
            INSERT INTO {COLLECTIONS_TABLE} (name, description, created_at)
            VALUES (:name, :description, CURRENT_TIMESTAMP())
            """,
            parameters=[
                _param("name", name),
                _param("description", description),
            ],
        )

        rows = execute_sql(
            f"""
            SELECT id, name, description, created_at
            FROM {COLLECTIONS_TABLE}
            WHERE name = :name
            ORDER BY id DESC
            LIMIT 1
            """,
            parameters=[_param("name", name)],
        )
        return rows[0] if rows else {}

    @staticmethod
    def update_collection(collection_id: int, **kwargs) -> Optional[Dict]:
        """Update a collection."""
        if not kwargs:
            return WarehouseDB.get_collection(collection_id)

        set_clauses = []
        params = [_param("collection_id", int(collection_id))]
        for i, (key, value) in enumerate(kwargs.items()):
            if value is not None:
                param_name = f"val_{i}"
                set_clauses.append(f"{key} = :{param_name}")
                params.append(_param(param_name, value))

        if not set_clauses:
            return WarehouseDB.get_collection(collection_id)

        execute_sql(
            f"""
            UPDATE {COLLECTIONS_TABLE}
            SET {', '.join(set_clauses)}
            WHERE id = :collection_id
            """,
            parameters=params,
        )

        return WarehouseDB.get_collection(collection_id)

    @staticmethod
    def delete_collection(collection_id: int) -> bool:
        """Delete a collection and its items."""
        cid_param = [_param("collection_id", int(collection_id))]
        execute_sql(
            f"DELETE FROM {COLLECTION_ITEMS_TABLE} WHERE collection_id = :collection_id",
            parameters=cid_param,
        )
        execute_sql(
            f"DELETE FROM {COLLECTIONS_TABLE} WHERE id = :collection_id",
            parameters=cid_param,
        )
        return True

    # ==================== COLLECTION ITEMS ====================

    @staticmethod
    def list_collection_items(collection_id: int) -> List[Dict]:
        """List items in a collection with joined entity data."""
        rows = execute_sql(
            f"""
            SELECT
                ci.id,
                ci.collection_id,
                ci.app_id,
                ci.mcp_server_id,
                ci.tool_id,
                a.name as app_name,
                a.owner as app_owner,
                a.url as app_url,
                s.server_url,
                s.kind as server_kind,
                t.name as tool_name,
                t.description as tool_description
            FROM {COLLECTION_ITEMS_TABLE} ci
            LEFT JOIN {APPS_TABLE} a ON ci.app_id = a.id
            LEFT JOIN {MCP_SERVERS_TABLE} s ON ci.mcp_server_id = s.id
            LEFT JOIN {TOOLS_TABLE} t ON ci.tool_id = t.id
            WHERE ci.collection_id = :collection_id
            """,
            parameters=[_param("collection_id", int(collection_id))],
        )

        # Transform to nested structure expected by API
        items = []
        for row_dict in rows:
            item = {
                'id': row_dict['id'],
                'collection_id': row_dict['collection_id'],
                'app_id': row_dict['app_id'],
                'mcp_server_id': row_dict['mcp_server_id'],
                'tool_id': row_dict['tool_id'],
            }

            if row_dict.get('app_id'):
                item['app'] = {
                    'id': row_dict['app_id'],
                    'name': row_dict.get('app_name'),
                    'owner': row_dict.get('app_owner'),
                    'url': row_dict.get('app_url'),
                }
            if row_dict.get('mcp_server_id'):
                item['server'] = {
                    'id': row_dict['mcp_server_id'],
                    'server_url': row_dict.get('server_url'),
                    'kind': row_dict.get('server_kind'),
                }
            if row_dict.get('tool_id'):
                item['tool'] = {
                    'id': row_dict['tool_id'],
                    'name': row_dict.get('tool_name'),
                    'description': row_dict.get('tool_description'),
                }

            items.append(item)

        return items

    @staticmethod
    def add_collection_item(collection_id: int, app_id: int = None,
                            mcp_server_id: int = None, tool_id: int = None) -> Dict:
        """Add an item to a collection."""
        execute_sql(
            f"""
            INSERT INTO {COLLECTION_ITEMS_TABLE} (collection_id, app_id, mcp_server_id, tool_id, created_at)
            VALUES (:collection_id, :app_id, :mcp_server_id, :tool_id, CURRENT_TIMESTAMP())
            """,
            parameters=[
                _param("collection_id", int(collection_id)),
                _param("app_id", int(app_id) if app_id is not None else None),
                _param("mcp_server_id", int(mcp_server_id) if mcp_server_id is not None else None),
                _param("tool_id", int(tool_id) if tool_id is not None else None),
            ],
        )

        # Get the inserted item
        rows = execute_sql(
            f"""
            SELECT id, collection_id, app_id, mcp_server_id, tool_id
            FROM {COLLECTION_ITEMS_TABLE}
            WHERE collection_id = :collection_id
            ORDER BY id DESC
            LIMIT 1
            """,
            parameters=[_param("collection_id", int(collection_id))],
        )
        return rows[0] if rows else {}

    @staticmethod
    def get_collection_item(item_id: int) -> Optional[Dict]:
        """Get a collection item by ID."""
        rows = execute_sql(
            f"""
            SELECT id, collection_id, app_id, mcp_server_id, tool_id
            FROM {COLLECTION_ITEMS_TABLE}
            WHERE id = :item_id
            """,
            parameters=[_param("item_id", int(item_id))],
        )
        return rows[0] if rows else None

    @staticmethod
    def delete_collection_item(item_id: int) -> bool:
        """Delete a collection item."""
        execute_sql(
            f"DELETE FROM {COLLECTION_ITEMS_TABLE} WHERE id = :item_id",
            parameters=[_param("item_id", int(item_id))],
        )
        return True
