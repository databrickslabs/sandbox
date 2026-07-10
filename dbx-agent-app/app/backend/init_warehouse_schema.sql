-- Initialize warehouse schema for registry API
-- This creates the core tables needed for the multi-agent registry

-- Apps table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.apps (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name STRING NOT NULL UNIQUE,
    owner STRING,
    url STRING,
    tags STRING,
    manifest_url STRING
);

-- Agents table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.agents (
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
);

-- Collections table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.collections (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name STRING NOT NULL UNIQUE,
    description STRING
);

-- MCP Servers table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.mcp_servers (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    app_id INT,
    server_url STRING NOT NULL,
    kind STRING NOT NULL,
    uc_connection STRING,
    scopes STRING
);

-- Tools table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.tools (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mcp_server_id INT NOT NULL,
    name STRING NOT NULL,
    description STRING,
    parameters STRING
);

-- Collection Items table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.collection_items (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection_id INT NOT NULL,
    app_id INT,
    mcp_server_id INT,
    tool_id INT
);

-- Discovery State table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.discovery_state (
    id INT PRIMARY KEY,
    is_running BOOLEAN NOT NULL,
    last_run_timestamp STRING,
    last_run_status STRING,
    last_run_message STRING
);

-- Supervisors table
CREATE TABLE IF NOT EXISTS serverless_dxukih_catalog.registry.supervisors (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    collection_id INT NOT NULL,
    app_name STRING NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    deployed_url STRING
);
