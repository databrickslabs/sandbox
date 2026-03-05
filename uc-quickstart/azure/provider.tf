provider "azurerm" {
  skip_provider_registration = true
  features {}
}

#Authenticating with Azure-managed Service Principal
provider "databricks" {
  alias                       = "workspace"
  host                        = var.databricks_host
  azure_workspace_resource_id = var.databricks_resource_id
  azure_client_id             = var.azure_client_id
  azure_client_secret         = var.azure_client_secret
  azure_tenant_id             = var.azure_tenant_id
}

// databricks at account level for account operations (groups)
provider "databricks" {
  alias               = "account"
  host                = "https://accounts.azuredatabricks.net"
  azure_client_id     = var.azure_client_id
  azure_client_secret = var.azure_client_secret
  account_id          = var.databricks_account_id
  azure_tenant_id     = var.azure_tenant_id
}