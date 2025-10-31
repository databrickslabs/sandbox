# README: Databricks Usage Dashboard v2.0

## Overview

This is version 2.0 of the popular [Usage Dashboard](https://docs.databricks.com/aws/en/admin/account-settings/usage), which provides users granular visibility into all billable usage across their Databricks account. 

All the usages in this dashboard are calculated based on the list price in USD unless the Global Filter 'Price Table' is toggled to use account\_prices instead.

*Note: This dashboard is not yet officially supported by Databricks, and still in preview. New updates to this version of the dashboard may be periodically released.*

Version 2.0 comes with a series of advanced functionality that leverages the best of new AI/BI Dashboard features. This dashboard helps answer:

* **Total actual and forecasted spend**   
  * What is total spend across your account? By workspace? By product?  
  * What is the forecasted total spend?  
* **Top spend drivers**  
  * What are the top 10 objects, by cost, in your account?  
  * Who owns the top objects, by cost, that match a certain tag? In which workspaces are they located?  
* **Spend breakdown by tags**  
  * What are the most popular tags (key, value pairs) in your account?  
  * What is the total spend tagged by specific key, value pairs?

## Data source

The dashboard is built on top of the following system tables:

* system.access.workspaces\_latest  
* system.billing.usage  
* system.billing.list\_prices  
* system.access.clean\_room\_events  
* system.serving.served\_entities  
* system.compute.clusters  
* system.lakeflow.jobs  
* system.lakeflow.pipelines  
* system.compute.warehouses

Users must have access to the above system tables in order to use the dashboard. 

## Installation Instructions

* Users can then [easily import it](https://docs.databricks.com/aws/en/dashboards/#import-a-dashboard-file) into their workspace of choice to load the dashboard.   
* Note on prerequisites: User should have system table access to view the dashboard.

## Support

Soon, this dashboard will be accessible directly in the product, like the current Usage Dashboard in Public Preview.  Admins can locate and import the dashboard directly from the Account Console in a few clicks. 

In the meantime, we are collecting feedback on the usability and performance of Usage Dashboard v2.0.  **Please share any feedback with your account team or [sadhana.bala@databricks.com](mailto:sadhana.bala@databricks.com)  directly**. We appreciate you testing out this feature early\!

