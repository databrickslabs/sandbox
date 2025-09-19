// Environment module helps provision the following:
// - Create the Catalogs and associated cloud infrastructure for specific environment
// - Enables System Schema for the workspace

module "prod_environment" {
  source = "./modules/environment"

  providers = {
    aws    = aws
    databricks = databricks.workspace
  }

  databricks_account_id  = var.databricks_account_id
  aws_account_id        = var.aws_account_id
  storage_prefix        = "${local.prefix}-${var.catalog_1}"
  tags                  = var.tags
  bucket_name           = "${local.prefix}-${var.catalog_1}"

  external_location_name = "${local.prefix}-${var.catalog_1}"

  catalog_name = "${local.prefix}-${var.catalog_1}"
}

module "dev_environment" {
  source = "./modules/environment"

  providers = {
    aws    = aws
    databricks = databricks.workspace
  }

  databricks_account_id  = var.databricks_account_id
  aws_account_id        = var.aws_account_id
  storage_prefix        = "${local.prefix}-${var.catalog_2}"
  tags                  = var.tags
  bucket_name           = "${local.prefix}-${var.catalog_2}"

  external_location_name = "${local.prefix}-${var.catalog_2}"

  catalog_name = "${local.prefix}-${var.catalog_2}"
}

module "sandbox_environment" {
  source = "./modules/environment"

  providers = {
    aws    = aws
    databricks = databricks.workspace
  }

  databricks_account_id  = var.databricks_account_id
  aws_account_id        = var.aws_account_id
  storage_prefix        = "${local.prefix}-${var.catalog_3}"
  tags                  = var.tags
  bucket_name           = "${local.prefix}-${var.catalog_3}"

  external_location_name = "${local.prefix}-${var.catalog_3}"

  catalog_name = "${local.prefix}-${var.catalog_3}"
}

#################################################################
//Create the different groups and asssign them to the workspaces

module "prod_sp_group" {
  source                = "./modules/users"

  providers = {
    databricks = databricks.account
  }
  group_name            = "${local.prefix}-${var.group_1}"
  databricks_workspace_id = var.databricks_workspace_id
}

module "developers_group" {
  source                = "./modules/users"

  providers = {
    databricks = databricks.account
  }
  group_name            = "${local.prefix}-${var.group_2}"
  databricks_workspace_id = var.databricks_workspace_id
}

module "sandbox_users_group" {
  source                = "./modules/users"

  providers = {
    databricks = databricks.account
  }
  group_name            = "${local.prefix}-${var.group_3}"
  databricks_workspace_id = var.databricks_workspace_id
}

#################################################################
// Grant privileges

module "grant_prod" {
  source       = "./modules/grants"

  providers = {
    databricks = databricks.workspace
  }

  catalog_name = "${local.prefix}-${var.catalog_1}"
  permissions  = var.catalog_1_permissions
  group_1_name = "${local.prefix}-${var.group_1}"
  group_2_name = "${local.prefix}-${var.group_2}"
  group_3_name = "${local.prefix}-${var.group_3}"
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.prod_environment]
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
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.dev_environment]
}


module "grant_sandbox" {
  source       = "./modules/grants"

  providers = {
    databricks = databricks.workspace
  }

  catalog_name = "${local.prefix}-${var.catalog_3}"
  permissions  = var.catalog_3_permissions
  group_1_name = "${local.prefix}-${var.group_1}"
  group_2_name = "${local.prefix}-${var.group_2}"
  group_3_name = "${local.prefix}-${var.group_3}"
  depends_on   = [module.sandbox_users_group, module.developers_group, module.prod_sp_group, module.sandbox_environment]
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

module "system_schema" {
  source                = "./modules/system_schema"
  providers = {
    databricks = databricks.workspace
  }
}

module "grant_system_schema" {
  source       = "./modules/grant_system_schema"
  providers = {
    databricks = databricks.workspace
  }

  group_1_name = "${local.prefix}-${var.group_1}"
  depends_on   = [module.system_schema]
}