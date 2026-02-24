# ============================================================================
# Genie Space ACLs - Set CAN_RUN permissions for configured groups
# ============================================================================
# Runs the genie_space.sh script to set ACLs on a Genie Space.
# Requires: genie_space_id variable.
# Grants CAN_RUN permission to all groups defined in var.groups.
# ============================================================================

resource "null_resource" "genie_space_acls" {
  count = var.genie_space_id != "" ? 1 : 0

  triggers = {
    space_id = var.genie_space_id
    groups   = join(",", keys(var.groups))
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/genie_space.sh set-acls"

    environment = {
      DATABRICKS_HOST          = var.databricks_workspace_host
      DATABRICKS_CLIENT_ID     = var.databricks_client_id
      DATABRICKS_CLIENT_SECRET = var.databricks_client_secret
      GENIE_SPACE_OBJECT_ID    = var.genie_space_id
      GENIE_GROUPS_CSV         = join(",", keys(var.groups))
    }
  }

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
  ]
}
