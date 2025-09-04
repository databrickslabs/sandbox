// Environment module helps provision the following:
// - Create the Catalogs and associated cloud infrastructure for specific environment
// - Enables System Schema for the workspace


// This creates a prod catalog with a seperate storage account, access_connector, storage credential and external location
module "prod_catalog" {
  source = "./modules/environment"

  providers = {
    azurerm    = azurerm
    databricks = databricks.workspace
  }

  access_connector_id    = ""
  access_connector_name  = "${local.prefix}-${var.catalog_3}-databricks-mi"
  resource_group         = var.resource_group
  location               = var.location
  storage_account_name   = "${local.dlsprefix}${var.catalog_3}acc"
  tags                   = local.tags
  storage_container_name = "${local.prefix}-${var.catalog_3}"

  storage_credential_name = "${local.prefix}-${var.catalog_3}"
  external_location_name  = "${local.prefix}-${var.catalog_3}"

  catalog_name = "${local.prefix}-${var.catalog_3}"
}

// This creates a dev catalog with a seperate storage account, access_connector, storage credential and external location
module "dev_catalog" {
  source = "./modules/environment"

  providers = {
    azurerm    = azurerm
    databricks = databricks.workspace
  }

  access_connector_id    = ""
  access_connector_name  = "${local.prefix}-${var.catalog_2}-databricks-mi"
  resource_group         = var.resource_group
  location               = var.location
  storage_account_name   = "${local.dlsprefix}${var.catalog_2}acc"
  tags                   = local.tags
  storage_container_name = "${local.prefix}-${var.catalog_2}"

  storage_credential_name = "${local.prefix}-${var.catalog_2}"
  external_location_name  = "${local.prefix}-${var.catalog_2}"

  catalog_name = "${local.prefix}-${var.catalog_2}"
}


// This creates a sandbox catalog with a seperate storage account, access_connector, storage credential and external location
module "sandbox_catalog" {
  source = "./modules/environment"

  providers = {
    azurerm    = azurerm
    databricks = databricks.workspace
  }

  access_connector_id    = ""
  access_connector_name  = "${local.prefix}-${var.catalog_1}-databricks-mi"
  resource_group         = var.resource_group
  location               = var.location
  storage_account_name   = "${local.dlsprefix}${var.catalog_1}acc"
  tags                   = local.tags
  storage_container_name = "${local.prefix}-${var.catalog_1}"

  storage_credential_name = "${local.prefix}-${var.catalog_1}"
  external_location_name  = "${local.prefix}-${var.catalog_1}"

  catalog_name = "${local.prefix}-${var.catalog_1}"
}

#################################################################
//Create the different groups and asssign them to the workspaces

module "prod_sp_group" {
  source = "./modules/users"

  providers = {
    databricks = databricks.account
  }

  group_name            = "${local.prefix}-${var.group_1}"
  databricks_account_id = var.databricks_account_id
  # databricks_account_username = var.databricks_account_username
  # databricks_account_password = var.databricks_account_password
  azure_client_id         = var.azure_client_id
  azure_client_secret     = var.azure_client_secret
  databricks_workspace_id = var.databricks_workspace_id
  azure_tenant_id         = var.azure_tenant_id
}

module "developers_group" {
  source = "./modules/users"

  providers = {
    databricks = databricks.account
  }

  group_name            = "${local.prefix}-${var.group_2}"
  databricks_account_id = var.databricks_account_id
  # databricks_account_username = var.databricks_account_username
  # databricks_account_password = var.databricks_account_password
  azure_client_id         = var.azure_client_id
  azure_client_secret     = var.azure_client_secret
  databricks_workspace_id = var.databricks_workspace_id
  azure_tenant_id         = var.azure_tenant_id
}

module "sandbox_users_group" {
  source = "./modules/users"

  providers = {
    databricks = databricks.account
  }

  group_name            = "${local.prefix}-${var.group_3}"
  databricks_account_id = var.databricks_account_id
  # databricks_account_username = var.databricks_account_username
  # databricks_account_password = var.databricks_account_password
  azure_client_id         = var.azure_client_id
  azure_client_secret     = var.azure_client_secret
  databricks_workspace_id = var.databricks_workspace_id
  azure_tenant_id         = var.azure_tenant_id
}

#################################################################
// Grant privileges

module "grant_prod" {
  source       = "./modules/grants"
  providers = {
    databricks = databricks.workspace
  }
  catalog_name = "${local.prefix}-${var.catalog_3}"
  permissions  = var.catalog_1_permissions
  group_1_name = "${local.prefix}-${var.group_1}"
  group_2_name = "${local.prefix}-${var.group_2}"
  group_3_name = "${local.prefix}-${var.group_3}"
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.prod_catalog]
}

module "grant_dev" {
  source       = "./modules/grants"
  providers = {
    databricks = databricks.workspace
  }
  catalog_name = "${local.prefix}-${var.catalog_2}"
  permissions  = var.catalog_2_permissions
  group_1_name = "${local.prefix}-${var.group_1}"
  group_2_name = "${local.prefix}-${var.group_2}"
  group_3_name = "${local.prefix}-${var.group_3}"
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.dev_catalog]
}

module "grant_sandbox" {
  source       = "./modules/grants"
  providers = {
    databricks = databricks.workspace
  }
  catalog_name = "${local.prefix}-${var.catalog_1}"
  permissions  = var.catalog_3_permissions
  group_1_name = "${local.prefix}-${var.group_1}"
  group_2_name = "${local.prefix}-${var.group_2}"
  group_3_name = "${local.prefix}-${var.group_3}"
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.sandbox_catalog]
}

#################################################################
// Create Cluster and Cluster policies per group

module "prod_cluster" {
  source = "./modules/compute"

  providers = {
    databricks = databricks.workspace
  }

  group_name = "${local.prefix}-${var.group_1}"
  environment = var.catalog_1

  depends_on   = [module.prod_sp_group, module.grant_prod]
}

module "dev_cluster" {
  source = "./modules/compute"

  providers = {
    databricks = databricks.workspace
  }

  group_name = "${local.prefix}-${var.group_2}"
  environment = var.catalog_2

  depends_on   = [module.developers_group, module.grant_dev]
}

module "sandbox_cluster" {
  source = "./modules/compute"

  providers = {
    databricks = databricks.workspace
  }

  group_name = "${local.prefix}-${var.group_3}"
  environment = var.catalog_3

  depends_on   = [module.sandbox_users_group, module.grant_sandbox]
}