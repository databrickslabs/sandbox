---
title: "DataMarket — Self-Service Data Catalog"
language: JavaScript
author: "Samir Raut"
date: 2026-06-29

tags:
- databricks-apps
- unity-catalog
- lakebase
- data-catalog
- data-governance
- access-management
---

# DataMarket — Self-Service Data Catalog on Databricks

A production-ready data catalog built entirely on Databricks. Gives every team a single place to discover certified data products, understand what they mean, and request access — without filing a ticket or waiting for an engineer.

Built on Databricks Apps, Unity Catalog, Lakebase, and Foundation Model APIs. No external dependencies.

![DataMarket](../../../docs/datamarket-thumbnail.png)

## What it does

- **Discover** — Browse and search all certified data products across your organization with domain filters, classification tags, and per-user access status
- **Request** — Submit access requests with business justification; data stewards review and approve
- **Govern** — Approvals automatically execute Unity Catalog `GRANT` statements via SQL Warehouse — no manual permission management
- **Ask AI** — Natural language data discovery backed by Databricks Foundation Model APIs (Llama 3.3-70B)
- **Insights** — Usage analytics and access request trends for stewards and managers

## Databricks Services Used

| Component | Service |
|---|---|
| Application hosting | Databricks Apps (serverless) |
| Data governance | Unity Catalog |
| OLTP backend | Lakebase Autoscaling (managed Postgres) |
| AI discovery | Foundation Model APIs (Llama 3.3-70B) |
| UC grant execution | SQL Statement Execution API |

## Deploy

### One-step CLI deploy (recommended for development)

```bash
git clone https://github.com/databricks-field-eng/datamarket.git
cd datamarket/src/app
databricks auth login --host https://your-workspace.azuredatabricks.net --profile my-profile
./deploy.sh --profile my-profile
```

The script handles everything: Lakebase project creation, schema init, SP grants, frontend build, workspace upload, and app deploy. Prints the app URL when done.

### Databricks Marketplace (coming soon)

A Marketplace listing is in progress. When published, no CLI or pre-build step will be required — the app builds its frontend on first startup via `manifest.yaml`.

## After Deploying

A 4-step onboarding wizard guides the admin through:
1. SQL Warehouse ID (auto-detected)
2. Branding (app name, logo, tagline)
3. Unity Catalog access grants for the app service principal
4. Creating the first data product

Admin access is automatic — the deployer's email is promoted to admin on first SSO login.

## Requirements

- Databricks workspace with Unity Catalog enabled
- Databricks CLI (`pip install databricks-cli`)
- Node.js ≥ 18
- Python 3

## Architecture

```
Browser → Databricks Apps (Express.js + React/Vite)
                ↓                    ↓
          Lakebase (Postgres)   Unity Catalog REST API
          access requests       catalog metadata
          approvals             GRANT execution
          audit log
```

## Source

Full source, documentation, and deploy guide: [github.com/databricks-field-eng/datamarket](https://github.com/databricks-field-eng/datamarket)
