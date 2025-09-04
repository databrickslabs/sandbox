// Create Databricks Storage Credential
resource "databricks_storage_credential" "db_uc_storage_cred" {
  name = var.storage_credential_name
  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.db_mi.id
  }
  comment = "Managed identity credential managed by TF"
  depends_on = [
    azurerm_role_assignment.db_mi_data_contributor
  ]
}

// Create Databricks External Location
resource "databricks_external_location" "db_ext_loc" {
  name = var.external_location_name
  url = format("abfss://%s@%s.dfs.core.windows.net",
    azurerm_storage_container.db_uc_catalog.name,
  azurerm_storage_account.db_uc_catalog.name)
  credential_name = databricks_storage_credential.db_uc_storage_cred.id
  comment         = "Managed by TF"
  depends_on = [
    databricks_storage_credential.db_uc_storage_cred,
    azurerm_role_assignment.db_mi_data_contributor
  ]
  force_destroy = true
}