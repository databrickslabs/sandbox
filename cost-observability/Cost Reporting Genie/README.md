# README: Cost Reporting Genie
## Overview
Gain visibility into your Databricks costs based on the **system.billing** tables. This Genie space focuses on **historical cost observability** - find out *what you spent, when, and on what*
## Data Sources
- system.billing.usage
- system.biling.list_prices
- system.billing.account_prices
- system.access.workspaces_latest
### **Current Capabilities and Limitations**
- ✅ Can answer historical cost and trend questions (by workspace, job, SKU, etc.)
- 📈 Can perform high-level cost forecasting using the `AI_FORECAST` function
- ⚠️ Cannot perform granular cost attribution on shared compute (e.g., warehouses, all-purpose clusters)
- 💰 Costs will reflect your usage at **list prices**, unless your account has `system.billing.account_prices` enabled (currently in **Private Preview** for AWS & GCP)
- 🚫 Cannot yet provide specific optimization recommendations to reduce cost
-  🎓 If your workspace has **Genie Research Agent** enabled, use *Research Agent mode* for deeper insights on exploratory questions.

## Installation Instructions

* Users can then easily import it into their workspace of choice using Genie Import/Export APIs (PrPr).
* Please reach out to your account team for export API instructions
* Note on prerequisites: User should have system table access to run the Genie space

## Support

We are collecting feedback on the usability and performance of Genie Space. Please share any feedback with your account team or sadhana.bala@databricks.com directly. We appreciate you testing out this feature early!"

### **Private Preview Notice**
- This Genie Space is in **Private Preview**. During this phase, Databricks may collect and use data related to this feature—such as inputs and outputs—to develop and test its functionality.
-  Learn more about previews: [https://docs.databricks.com/aws/en/admin/workspace-settings/manage-previews](https://docs.databricks.com/aws/en/admin/workspace-settings/manage-previews)
-  ⚠️ **Note:** Please review all Genie responses for accuracy, as model outputs may not always be complete or correct.
