// Create azure managed identity to be used by Databricks storage credential
resource "azurerm_databricks_access_connector" "db_mi" {
  name                = var.access_connector_name
  resource_group_name = var.resource_group
  location            = var.location
  identity {
    type = "SystemAssigned"
  }
}

// Create a storage account to be used by catalog
resource "azurerm_storage_account" "db_uc_catalog" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group
  location                 = var.location
  tags                     = var.tags
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

// Create a container in storage account to be used by unity catalog metastore as root storage
resource "azurerm_storage_container" "db_uc_catalog" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.db_uc_catalog.name
  container_access_type = "private"
}

// Assign the Storage Blob Data Contributor role to managed identity to allow unity catalog to access the storage
resource "azurerm_role_assignment" "db_mi_data_contributor" {
  scope                = azurerm_storage_account.db_uc_catalog.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.db_mi.identity[0].principal_id
}