# Databricks Serverless Migration Assistance Dashboard

This dashboard provides visibility into **Databricks Serverless** usage and migration opportunities across your jobs, helping organizations understand and optimize their transition to serverless compute.

> **Note:** This dashboard is **not officially supported by Databricks** and is provided as a **community contribution**. Estimates may not reflect actual billing and require [system tables](https://docs.databricks.com/administration-guide/system-tables/index.html) and a **Unity Catalog-enabled workspace**.

---

## What It Does

This dashboard helps answer:

- Which workloads are suitable for migration to serverless compute?
- What is the potential cost impact of migrating to serverless?

It leverages the following system tables:
- `system.billing.usage`
- `system.billing.list_prices`
- `system.lakeflow.job_run_timeline`

---

## Installation Instructions

To use this dashboard:

1. Navigate to your **Databricks Workspace**.
2. Go to the **Dashboards** section.
3. Click on **Create Dashboard**, then use the dropdown arrow to select **Import dashboard from file**.
4. Upload the included JSON file:
   - `Serverless Migration Assistance Dashboard.lvdash.json`

---

## Community Support

This tool is community-supported and intended to help customers evaluate and plan their migration to Databricks SQL Serverless. Contributions, improvements, and issues are welcome via pull requests or GitHub Issues.
