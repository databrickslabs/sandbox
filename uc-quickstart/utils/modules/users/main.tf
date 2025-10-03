# Create Databricks group at account level
resource "databricks_group" "account_group" {
  display_name = var.group_name
}

# Assign group to workspace
resource "databricks_mws_permission_assignment" "add_user_group" {
  workspace_id = var.databricks_workspace_id
  principal_id = databricks_group.account_group.id
  permissions  = ["USER"]
}
