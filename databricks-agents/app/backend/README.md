# Multi-Agent Registry API

The central backend for the agentic-knowledge-graph project. A FastAPI service that discovers, indexes, and provides access to everything in a Databricks workspace — agents, tools, MCP servers, Unity Catalog assets, workspace objects, and more.

## What It Does

**Asset Discovery & Indexing** — Crawls Unity Catalog (tables, views, functions, models, volumes) and workspace objects (notebooks, jobs, dashboards, pipelines). Discovers Databricks Apps that expose MCP endpoints and registers their tools.

**Agent & Tool Registry** — Registers AI agents with capabilities, endpoints, and system prompts. Catalogs MCP servers and tools. Lets users curate collections and generate supervisor orchestrators from them.

**Search & Chat** — Semantic search across all indexed assets via vector embeddings. Chat interface with tool calling against registered MCP servers. Conversation persistence with MLflow tracing.

## Architecture

```
Webapp (React)
    |
Registry API (FastAPI)  <-- this service
    |
    +-- Discovery Service     (MCP endpoint probing, workspace/catalog crawlers)
    +-- Agent/Tool Registry   (CRUD, collections, supervisor generation)
    +-- Search Service        (vector embeddings, semantic search)
    +-- Chat Service          (LLM chat with tool calling, MLflow traces)
    +-- A2A Protocol          (agent-to-agent coordination via JSON-RPC 2.0)
    |
Databricks (Unity Catalog, SQL Warehouse, MLflow, Foundation Models, Apps)
```

## Domain Models

15 SQLAlchemy models across 4 domains:

### Core Registry

| Model | Table | Purpose |
|-------|-------|---------|
| App | `apps` | Databricks Apps metadata (name, url, owner) |
| MCPServer | `mcp_servers` | MCP server configs (managed/external/custom), FK to App |
| Tool | `tools` | Individual tools from MCP servers (name, params, description) |
| Collection | `collections` | User-curated groupings |
| CollectionItem | `collection_items` | Polymorphic join (app, server, or tool) |

### Agents & Coordination

| Model | Table | Purpose |
|-------|-------|---------|
| Agent | `agents` | Agent entities with capabilities, endpoint, system prompt, A2A fields |
| Supervisor | `supervisors` | Generated supervisor metadata from collections |
| A2ATask | `a2a_tasks` | Work assigned to agents via A2A protocol |

### Asset Indexing

| Model | Table | Purpose |
|-------|-------|---------|
| CatalogAsset | `catalog_assets` | UC assets (tables, views, functions) with columns, tags, properties |
| WorkspaceAsset | `workspace_assets` | Workspace objects (notebooks, jobs, dashboards) with metadata |
| AssetEmbedding | `asset_embeddings` | Vector embeddings for semantic search |
| AssetRelationship | `asset_relationships` | Lineage/dependency edges between assets |

### Operational

| Model | Table | Purpose |
|-------|-------|---------|
| Conversation | `conversations` | Chat conversation metadata |
| ConversationMessage | `conversation_messages` | Individual messages with trace links |
| AuditLog | `audit_log` | Append-only governance trail |
| DiscoveryState | `discovery_state` | Background crawl/discovery status |

### Entity Relationships

```
apps (1) ───< mcp_servers (1) ───< tools
  |                |                  |
  +----------------+------------------+---< collection_items >--- collections
                                      |
agents ───< a2a_tasks                 |
                                      |
catalog_assets ───< asset_embeddings  |
workspace_assets ──< asset_relationships
```

## API Routes

20 route modules under `/api`:

### Discovery & Indexing
- `GET  /api/discovery/workspaces` — List Databricks CLI profiles with auth status
- `POST /api/discovery/refresh` — Discover MCP servers from workspace apps, catalog, or custom URLs
- `GET  /api/discovery/status` — Check background discovery status
- `POST /api/catalog-assets/crawl` — Crawl Unity Catalog (tables, views, functions, volumes)
- `POST /api/workspace-assets/crawl` — Crawl workspace objects (notebooks, jobs, dashboards)

### Agent Management
- `GET|POST /api/agents` — List / create agents
- `GET|PUT|DELETE /api/agents/{id}` — Get / update / delete agent
- `GET /api/agents/{id}/card` — A2A-compliant Agent Card

### MCP Servers & Tools
- `GET|POST /api/mcp-servers` — List / create MCP server configs
- `GET|PUT|DELETE /api/mcp-servers/{id}` — CRUD
- `GET|POST /api/tools` — List / create tools
- `GET|PUT|DELETE /api/tools/{id}` — CRUD

### Collections & Supervisors
- `GET|POST /api/collections` — List / create collections
- `POST /api/collections/{id}/items` — Add app/server/tool to collection
- `POST /api/supervisors/generate` — Generate supervisor code from a collection
- `GET /api/supervisors/{id}/preview` — Preview generated files
- `POST /api/supervisors/{id}/download` — Download as zip

### Search & Chat
- `POST /api/search` — Semantic search across all indexed assets
- `POST /api/chat` — Chat with tool calling (SSE streaming)
- `GET|POST /api/conversations` — Conversation history
- `GET /api/lineage/{asset_id}` — Asset lineage graph

### Infrastructure
- `GET /health` — Health check
- `GET /api/audit-log` — Query audit trail
- `POST /api/a2a` — A2A JSON-RPC 2.0 dispatch

## Services

16 service modules implementing business logic:

| Service | File | Purpose |
|---------|------|---------|
| DiscoveryService | `discovery.py` | Orchestrates workspace app enumeration, MCP probing, catalog discovery |
| MCPClient | `mcp_client.py` | JSON-RPC 2.0 client for MCP `tools/list` calls |
| ToolParser | `tool_parser.py` | Normalizes MCP tool metadata |
| CatalogCrawler | `catalog_crawler.py` | Walks UC hierarchy via Databricks SDK |
| WorkspaceCrawler | `workspace_crawler.py` | Indexes workspace objects via SDK |
| LineageCrawler | `lineage_crawler.py` | Tracks asset dependencies |
| EmbeddingService | `embedding.py` | Generates vectors via Databricks Foundation Models |
| SearchService | `search.py` | Semantic search with vector similarity |
| GeneratorService | `generator.py` | Generates supervisor code from Jinja2 templates |
| ChatContext | `chat_context.py` | Conversation memory and context management |
| AgentChat | `agent_chat.py` | Agent chat with tool calling |
| CollectionsService | `collections.py` | Collection CRUD with item management |
| A2AClient | `a2a_client.py` | Agent-to-Agent protocol client |
| WorkspaceProfiles | `workspace_profiles.py` | Parses `~/.databrickscfg`, validates auth |
| AuditService | `audit.py` | Append-only audit logging |
| A2ANotifications | `a2a_notifications.py` | Webhook notifications for A2A tasks |

## Project Structure

```
registry-api/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, router registration
│   ├── config.py               # Pydantic settings from env vars
│   ├── database.py             # SQLAlchemy engine, session factory
│   ├── db_adapter.py           # Database abstraction (SQLite / Databricks SQL)
│   ├── middleware/
│   │   └── auth.py             # OBO authentication middleware
│   ├── models/                 # 15 SQLAlchemy models
│   ├── routes/                 # 20 FastAPI route modules
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # 16 business logic modules
│   └── templates/              # Jinja2 templates for supervisor generation
├── alembic/                    # Database migrations
├── tests/                      # Pytest test suite
├── app.yaml                    # Databricks Apps deployment config
├── deploy.sh                   # Deployment script
├── requirements.txt            # Python dependencies
└── README.md
```

## Setup

### Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# SQLite for local dev (default)
export DATABASE_URL=sqlite:///./data/registry.db

# Run with auto-reload
uvicorn app.main:app --reload --port 8000
```

### Databricks Apps Deployment

```bash
# Sync and deploy (uses fe-vm-serverless-dxukih profile)
./deploy.sh

# Or manually:
databricks sync . /Workspace/Shared/apps/registry-api --profile fe-vm-serverless-dxukih --full \
  --exclude ".venv" --exclude "__pycache__" --exclude ".git" --exclude "*.pyc" --exclude "*.db"
databricks apps deploy registry-api --source-code-path /Workspace/Shared/apps/registry-api \
  --profile fe-vm-serverless-dxukih
```

**Deployed URL**: `https://registry-api-7474660127789418.aws.databricksapps.com`

## Configuration

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Connection string | `sqlite:///./data/registry.db` |

### Databricks

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABRICKS_HOST` | Workspace URL | (from SDK config) |
| `DATABRICKS_TOKEN` | Access token | (from SDK config) |
| `DATABRICKS_CONFIG_PROFILE` | CLI profile | (none) |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse ID | (none) |

### LLM & Embeddings

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_ENDPOINT` | Chat model endpoint | `databricks-claude-sonnet-4-5` |
| `EMBEDDING_MODEL` | Embedding model | `databricks-bge-large-en` |
| `EMBEDDING_DIMENSION` | Vector dimensions | `1024` |

### MCP & A2A

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_CATALOG_URL` | Central MCP catalog endpoint | (none, gracefully skipped) |
| `A2A_PROTOCOL_VERSION` | A2A protocol version | `0.3.0` |
| `A2A_BASE_URL` | Base URL for A2A endpoints | (none) |

### Server

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `HOST` | Bind address | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000,...` |
| `AUTH_ENABLED` | Enable auth middleware | `true` |

## Database Migrations

```bash
alembic upgrade head                              # Apply all migrations
alembic revision --autogenerate -m "description"  # Generate new migration
alembic history                                   # View history
alembic downgrade -1                              # Rollback one
```

## Testing

```bash
pytest                           # Run all tests
pytest tests/test_discovery.py   # Run specific test file
pytest -v --tb=short             # Verbose with short tracebacks
```
