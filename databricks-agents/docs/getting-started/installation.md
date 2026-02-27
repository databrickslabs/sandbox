# Installation

## Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **pip** package manager
- **Databricks CLI** (only needed for deployment; not required for local development)

## Install from PyPI

```bash
pip install databricks-agents
```

## Install for development

Clone the repository and install in editable mode with dev dependencies:

```bash
git clone https://github.com/databricks-labs/databricks-agents.git
cd databricks-agents
pip install -e ".[dev]"
```

The `[dev]` extra installs testing and linting tools: pytest, pytest-asyncio, pytest-cov, black, ruff, and mypy.

## Verify the installation

```bash
python -c "from databricks_agents import AgentApp; print('OK')"
```

You should see `OK` printed with no errors.

## What gets installed

The SDK has a small dependency footprint:

| Package | Purpose |
|---|---|
| `fastapi` | HTTP framework (AgentApp extends FastAPI) |
| `uvicorn` | ASGI server for local development |
| `pydantic` | Data validation and settings |
| `httpx` | Async HTTP client for A2A communication |
| `databricks-sdk` | Databricks workspace API client |

## Databricks CLI (optional)

The Databricks CLI is only needed when you want to deploy your agent to Databricks Apps or register it in Unity Catalog from the command line.

Install it separately:

```bash
pip install databricks-cli
```

Configure a profile:

```bash
databricks configure --profile my-workspace
```

See the [Databricks CLI documentation](https://docs.databricks.com/en/dev-tools/cli/index.html) for full setup instructions.

## Next steps

- [Quick Start](quickstart.md) -- create and run an agent in 5 minutes
- [Your First Agent](first-agent.md) -- a deeper walkthrough with multiple tools
