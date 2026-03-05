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
