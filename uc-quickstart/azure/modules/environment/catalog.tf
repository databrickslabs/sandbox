// Create Databricks Catalog
resource "databricks_catalog" "uc_quickstart_sandbox" {
  name         = var.catalog_name
  storage_root = format(
    "abfss://%s@%s.dfs.core.windows.net",
    azurerm_storage_container.db_uc_catalog.name,
  azurerm_storage_account.db_uc_catalog.name
  )
  depends_on = [
    databricks_external_location.db_ext_loc
  ]
  # Made configurable to prevent accidental data loss in production
  # This setting controls whether the catalog and all its contents are deleted on terraform destroy
  force_destroy = var.force_destroy_catalog
}