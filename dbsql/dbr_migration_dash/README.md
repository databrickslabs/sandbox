# Databricks Runtime Deprecation Impact Dashboard

Leaving this README in place, but code and new solution (backed by DABs) has migrated to dbsql/dbr_eos folder

This dashboard provides visibility into **Databricks Runtime (DBR)** usage across both **Jobs** and **All-Purpose clusters**, helping organizations understand and mitigate risks associated with **runtime deprecations** or **end-of-support timelines**.

> **Note:** This dashboard is **not officially supported by Databricks** and is provided as a **community contribution**. Estimates may not reflect actual billing and require [system tables](https://docs.databricks.com/administration-guide/system-tables/index.html) and a **Unity Catalog-enabled workspace**.

---

## What It Does

This dashboard helps answer:

- Which DBR versions are in use across jobs and clusters?
- How much spend is associated with unsupported or deprecated runtimes?
- Which users and jobs are impacted?
- What’s the annualized cost exposure to legacy runtimes?

It leverages the following system tables:
- `system.compute.clusters`
- `system.billing.usage`
- `system.billing.list_prices`

---

## Installation Instructions

To use this dashboard:

1. Navigate to your **Databricks Workspace**.
2. Go to the **Dashboards** section.
3. Click on **Create Dashboard**, then use the dropdown arrow to select **Import dashboard from file**.
4. Upload the included JSON file:
   - `Databricks Runtime Deprecation Impact Dashboard.lvdash.json`

---

## Community Support

This tool is community-supported and intended to help customers proactively manage the Databricks Runtime (DBR) lifecycle. Contributions, improvements, and issues are welcome via pull requests or GitHub Issues.