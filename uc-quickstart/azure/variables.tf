locals {
  prefix    = "ucqs-${random_string.naming.result}"
  dlsprefix = "ucqs${random_string.naming.result}"
  tags = {
    project = "uc-quickstart"
  }
}

resource "random_string" "naming" {
  special = false
  upper   = false
  length  = 6
}

variable "resource_group" {
  description = "The Azure resource group name"
  type        = string
}

variable "location" {
  description = "The Azure location"
  type        = string
  default     = "Australia East"
}

variable "databricks_account_id" {}
variable "databricks_workspace_id" {}
variable "databricks_host" {}
variable "databricks_token" {}

#Authenticating with Azure-managed Service Principal
variable "databricks_resource_id" {
  default = "databricks_resource_id"
}
variable "azure_client_id" {
  default = "sp_client_id"
}
variable "azure_client_secret" {
  default = "sp_client_secret"
}
variable "azure_tenant_id" {
  default = "azure_tenant_id"
}

#############
# Configure catalog names to deploy
variable "catalog_1" {
  type    = string
  default = "sandbox"
}

variable "catalog_2" {
  type    = string
  default = "dev"
}

variable "catalog_3" {
  type    = string
  default = "prod"
}

#############
# Configure Account Group names to deploy
variable "group_1" {
  default = "production_sp"
}

variable "group_2" {
  default = "developers"
}

variable "group_3" {
  default = "sandbox_users"
}

#############
# Configure catalog permissions for different groups
variable "catalog_1_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["USE_CATALOG", "SELECT"]
    group_3 = []
  }
}

variable "catalog_2_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["ALL_PRIVILEGES"]
    group_3 = []
  }
}

variable "catalog_3_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["ALL_PRIVILEGES"]
    group_3 = ["ALL_PRIVILEGES"]
  }
}