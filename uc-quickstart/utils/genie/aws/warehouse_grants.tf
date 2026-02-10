# ============================================================================
# Genie Space: CAN USE on SQL warehouse
# ============================================================================
# Grants CAN_USE on the Genie warehouse (created in genie_warehouse.tf or
# genie_use_existing_warehouse_id) to the five finance groups and the "users"
# group so all workspace users can run queries in Genie.
# Uses try() so count is known at plan time (no dependency on created endpoint id).
# ============================================================================

resource "databricks_permissions" "genie_warehouse_use" {
  provider = databricks.workspace
  # When endpoint is created, use its id; when using existing warehouse, use var (try returns 2nd arg when endpoint has count=0)
  sql_endpoint_id = try(databricks_sql_endpoint.genie_warehouse[0].id, coalesce(var.genie_use_existing_warehouse_id, var.genie_default_warehouse_id))

  depends_on = [
    databricks_sql_endpoint.genie_warehouse,
    databricks_group.finance_groups,
    databricks_mws_permission_assignment.finance_group_assignments,
  ]

  access_control {
    group_name       = "users"
    permission_level = "CAN_USE"
  }
  access_control {
    group_name       = "Junior_Analyst"
    permission_level = "CAN_USE"
  }
  access_control {
    group_name       = "Senior_Analyst"
    permission_level = "CAN_USE"
  }
  access_control {
    group_name       = "US_Region_Staff"
    permission_level = "CAN_USE"
  }
  access_control {
    group_name       = "EU_Region_Staff"
    permission_level = "CAN_USE"
  }
  access_control {
    group_name       = "Compliance_Officer"
    permission_level = "CAN_USE"
  }
}
