"""
Initialize warehouse schema if using Databricks SQL Warehouse.

This module provides a function to create tables in the warehouse
before the app starts up and attempts to query them.
"""

import logging
from app.db_warehouse import execute_sql, CATALOG, SCHEMA

logger = logging.getLogger(__name__)


def init_warehouse_tables():
    """
    Create warehouse tables if they don't exist.
    This runs on app startup when using warehouse backend.
    """
    tables_ddl = [
        # Apps table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.apps (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name STRING NOT NULL UNIQUE,
            owner STRING,
            url STRING,
            tags STRING,
            manifest_url STRING
        )
        """,
        # Agents table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.agents (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name STRING NOT NULL UNIQUE,
            description STRING,
            capabilities STRING,
            status STRING NOT NULL DEFAULT 'draft',
            collection_id INT,
            app_id INT,
            endpoint_url STRING,
            auth_token STRING,
            a2a_capabilities STRING,
            skills STRING,
            protocol_version STRING DEFAULT '0.3.0',
            system_prompt STRING,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """,
        # Collections table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.collections (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name STRING NOT NULL UNIQUE,
            description STRING
        )
        """,
        # MCP Servers table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.mcp_servers (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            app_id INT,
            server_url STRING NOT NULL,
            kind STRING NOT NULL,
            uc_connection STRING,
            scopes STRING
        )
        """,
        # Tools table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.tools (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            mcp_server_id INT NOT NULL,
            name STRING NOT NULL,
            description STRING,
            parameters STRING
        )
        """,
        # Collection Items table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.collection_items (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            collection_id INT NOT NULL,
            app_id INT,
            mcp_server_id INT,
            tool_id INT
        )
        """,
        # Discovery State table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.discovery_state (
            id INT PRIMARY KEY,
            is_running BOOLEAN NOT NULL DEFAULT FALSE,
            last_run_timestamp STRING,
            last_run_status STRING,
            last_run_message STRING
        )
        """,
        # Supervisors table
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.supervisors (
            id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            collection_id INT NOT NULL,
            app_name STRING NOT NULL,
            generated_at TIMESTAMP NOT NULL,
            deployed_url STRING
        )
        """,
    ]

    logger.info(f"[WAREHOUSE-INIT] Initializing warehouse schema: {CATALOG}.{SCHEMA}")

    for i, ddl in enumerate(tables_ddl, 1):
        try:
            execute_sql(ddl)
            logger.info(f"[WAREHOUSE-INIT] Table {i}/{len(tables_ddl)} initialized")
        except Exception as e:
            logger.error(f"[WAREHOUSE-INIT] Failed to create table {i}: {e}")
            raise

    logger.info("[WAREHOUSE-INIT] All tables initialized successfully")
