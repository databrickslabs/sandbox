# Judge Builder Development Instructions

## Prerequisites

- Python 3.9+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/) v0.230.0+

## Setup

```bash
git clone https://github.com/databricks-solutions/judge-builder.git
cd judge-builder
./setup.sh
```

This will
   - Install Python dependencies using uv
   - Install Node.js dependencies
   - Set up environment configuration

## Deploy

To deploy the application to Databricks Apps:

```bash
./deploy.sh
```

This will:
- Build the frontend
- Sync code to Databricks workspace
- Create and deploy the Databricks App

## Develop
```bash
./dev/watch.sh
```
This runs both the FastAPI backend (port 8001) and React frontend (port 3000) in development mode. The API documentation can be found at: http://localhost:8001/docs
