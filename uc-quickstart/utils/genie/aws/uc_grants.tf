# ============================================================================
# Unity Catalog Data Access Grants
# ============================================================================
# Uses databricks_grant (singular) which is ADDITIVE — it only manages the
# grants for each specified principal without removing existing permissions
# from other principals on the catalog.
#
# Multi-catalog: catalogs are auto-derived from fully-qualified entity names
# in tag_assignments and catalog fields in fgac_policies. No manual list needed.
# ============================================================================

locals {
  _ta_catalogs = [
    for ta in var.tag_assignments :
    split(".", ta.entity_name)[0]
  ]

  _fgac_catalogs = [
    for p in var.fgac_policies :
    p.catalog
  ]

  all_catalogs = distinct(concat(
    local._ta_catalogs,
    local._fgac_catalogs,
  ))
}

resource "databricks_grant" "terraform_sp_manage_catalog" {
  for_each = toset(local.all_catalogs)

  provider   = databricks.workspace
  catalog    = each.value
  principal  = var.databricks_client_id
  privileges = ["USE_CATALOG", "USE_SCHEMA", "EXECUTE", "MANAGE", "CREATE_FUNCTION"]
}

resource "databricks_grant" "catalog_access" {
  for_each = {
    for pair in setproduct(local.all_catalogs, keys(var.groups)) :
    "${pair[0]}|${pair[1]}" => { catalog = pair[0], group = pair[1] }
  }

  provider   = databricks.workspace
  catalog    = each.value.catalog
  principal  = each.value.group
  privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
  ]
}
