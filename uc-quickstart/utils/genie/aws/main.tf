# ============================================================================
# ABAC Account Groups - Generic Terraform Configuration
# ============================================================================
# Creates account-level groups, assigns them to a workspace, and grants
# consumer entitlements. Groups are driven entirely by var.groups.
# ============================================================================

# ----------------------------------------------------------------------------
# Create Account-Level Groups
# ----------------------------------------------------------------------------

resource "databricks_group" "groups" {
  for_each = var.groups

  provider     = databricks.account
  display_name = each.key
}

# ----------------------------------------------------------------------------
# Assign Groups to Workspace
# ----------------------------------------------------------------------------

resource "databricks_mws_permission_assignment" "group_assignments" {
  for_each = databricks_group.groups

  provider     = databricks.account
  workspace_id = var.databricks_workspace_id
  principal_id = each.value.id
  permissions  = ["USER"]
}

# ----------------------------------------------------------------------------
# Grant Consumer Entitlements (Databricks One UI only)
# ----------------------------------------------------------------------------
# workspace_consume cannot be combined with workspace_access or databricks_sql_access.

resource "databricks_entitlements" "group_entitlements" {
  for_each = databricks_group.groups

  provider = databricks.workspace
  group_id = each.value.id

  workspace_consume = true

  depends_on = [databricks_mws_permission_assignment.group_assignments]
}
