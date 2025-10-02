# DBR End-of-Service Monitor

This repository contains two main components:

## 1. `dbr-eos-monitor-dabs/` — Databricks Asset Bundle (DABs)
The **`dbr-eos-monitor-dabs/`** folder contains a [Databricks Asset Bundle](https://docs.databricks.com/en/dev-tools/bundles/index.html) that automates:

- **Refreshing the DBR lookup table** — Updates data about cluster DBR versions and their end-of-service dates.
- **Refreshing the Lakeview dashboard** — Ensures the “DBR Monitor Dashboard” always displays the latest DBR cluster status.

### Key components
- **Jobs:** `DBR_Monitor_Refresh`  scheduled to run 6am daily.
  - **Task 1:** Runs the `DBR_Lookup_Table.ipynb` notebook to update DBR metadata.  
  - **Task 2:** Refreshes the `DBR Monitor Dashboard` bound to a Serverless SQL Warehouse.
- **Serverless SQL Warehouse:** `DBR Monitor Serverless` — Created automatically for dashboard queries.
- **Dashboard:** `DBR Monitor Dashboard` — Shows clusters and days until DBR end-of-service.

### How to deploy
1. Clone this repo into your Databricks workspace **Git Folder**.
2. In your Databricks workspace, go to **Create → Git Folder**, select **Sparse checkout mode** and paste this Git URL (https://github.com/databrickslabs/sandbox.git).
3. Paste **dbsql/dbr_eos** in the Cone patterns box
4. Give the Git folder name something useful like, "DBR_End_of_Service"
5. Click **"Open in asset bundle editor"**.
6. Click in the top right, **"deploy bundle"**.
7. After deployment, open the created Dashboard (DBR Monitor Dashboard) and the Job (DBR Monitor Refresh).

---

## 2. `alerts/` — DBR EOS Alerts (not DABs-managed)
The **`alerts/`** folder contains definitions and scripts for **Alerts v2** that **notify recipients when job or interactive clusters are running a DBR that is past end-of-service**.

### Update notifications and custom template
- **Please update** the alert notifications fields to include all who should be notified of clusters running EOS DBR
- **Please update** the custom template href for the dashboard to reflect your `DBR Monitor Dashboard` URL

### Why not in DABs?
Databricks Asset Bundles do **not** currently support managing Alerts v2 directly.  
Instead, the `alerts/` folder:
- Stores the alert configuration in JSON.
- Pulls the alerts to your workspace via GIT.
- The alert runs on a Serverless SQL Warehouse, scheduled to run 6:20am daily.
- It queries for clusters where: days_until_eos <= threshold
- Once you update the notifications then they'll be alerted when triggered
