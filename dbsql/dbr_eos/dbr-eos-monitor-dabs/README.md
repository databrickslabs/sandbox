# Databricks Runtime EOS Monitor - Asset Bundle
Monitor and alert on DBR at or nearing end of service.

This bundle creates:
- A notebook-based refresh job (`DBR_Lookup_Table.ipynb`)
- A dashboard (`DBR Days Until End Of Service Dashboard.lvdash.json`) that will be created in your workspace on deploy

## How to Use

## Quickstart (Workspace UI)
1. Clone this repo into your Databricks workspace **Git Folder**.
2. In your Databricks workspace, go to **Create → Git Folder**, select **Sparse checkout mode** and paste this Git URL (https://github.com/databrickslabs/sandbox.git).
3. Paste **dbsql/dbr_eos** in the Cone patterns box
4. Give the Git folder name something useful like, "DBR_End_of_Service"
5. Click **"Open in asset bundle editor"**.
6. Click in the top right, **"deploy bundle"**.
7. After deployment, open the created Dashboard (DBR Monitor Dashboard) and the Job (DBR Monitor Refresh).

## Quickstart (CLI)
```bash
# Use your workspace profile
databricks bundle validate -t dev
databricks bundle deploy -t dev

