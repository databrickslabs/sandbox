# ============================================================================
# Genie Space ACLs - Set CAN_RUN permissions for finance groups
# ============================================================================
# This resource runs the genie_space.sh script to set ACLs on a Genie Space.
# Requires: genie_space_id variable.
#
# Authentication: Uses the same Service Principal OAuth M2M credentials
# as the workspace provider (databricks_client_id/databricks_client_secret).
#
# The script grants CAN_RUN permission to these groups:
#   - Junior_Analyst
#   - Senior_Analyst
#   - US_Region_Staff
#   - EU_Region_Staff
#   - Compliance_Officer
# ============================================================================

resource "null_resource" "genie_space_acls" {
  count = var.genie_space_id != "" ? 1 : 0

  triggers = {
    # Re-run when space ID or groups change
    space_id = var.genie_space_id
    groups   = join(",", ["Junior_Analyst", "Senior_Analyst", "US_Region_Staff", "EU_Region_Staff", "Compliance_Officer"])
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/genie_space.sh set-acls"

    environment = {
      DATABRICKS_HOST          = var.databricks_workspace_host
      DATABRICKS_CLIENT_ID     = var.databricks_client_id
      DATABRICKS_CLIENT_SECRET = var.databricks_client_secret
      GENIE_SPACE_OBJECT_ID    = var.genie_space_id
    }
  }

  depends_on = [
    databricks_group.finance_groups,
    databricks_mws_permission_assignment.finance_group_assignments
  ]
}
