resource "databricks_grant" "system_catalog" {
  catalog = "system"
  principal  = var.group_1_name
  privileges = ["USE_CATALOG"]
}

resource "databricks_grant" "system_schemas" {
  for_each = toset(["system.access", "system.billing", "system.compute", "system.marketplace", "system.storage"])
  schema    = each.value
  principal  = var.group_1_name
  privileges = ["USE_SCHEMA", "SELECT"]
}