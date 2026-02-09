# ============================================================================
# Genie Space: CAN USE on SQL warehouse
# ============================================================================
# Grants CAN_USE on the SQL warehouse designated for the Genie Space to the
# five finance groups so consumers can run queries. Only created when
# genie_default_warehouse_id is set.
# ============================================================================

resource "databricks_permissions" "genie_warehouse_use" {
  count = var.genie_default_warehouse_id != "" ? 1 : 0

  provider         = databricks.workspace
  sql_endpoint_id  = var.genie_default_warehouse_id

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
