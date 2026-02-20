# ============================================================================
# Unity Catalog Data Access Grants
# ============================================================================
# Uses databricks_grant (singular) which is ADDITIVE — it only manages the
# grants for each specified principal without removing existing permissions
# from other principals on the catalog.
# ============================================================================

# Grant the Terraform SP explicit catalog/schema access so it can create
# FGAC policies referencing masking UDFs in this catalog.
resource "databricks_grant" "terraform_sp_manage_catalog" {
  provider   = databricks.workspace
  catalog    = var.uc_catalog_name
  principal  = var.databricks_client_id
  privileges = ["USE_CATALOG", "USE_SCHEMA", "EXECUTE", "MANAGE"]
}

resource "databricks_grant" "catalog_access" {
  for_each = toset(keys(var.groups))

  provider   = databricks.workspace
  catalog    = var.uc_catalog_name
  principal  = each.key
  privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
  ]
}
