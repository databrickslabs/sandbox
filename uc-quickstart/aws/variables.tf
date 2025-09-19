resource "random_string" "naming" {
  special = false
  upper   = false
  length  = 6
}

locals {
  prefix = "uc-quickstart-${random_string.naming.result}"
}

variable "tags" {
  default     = {}
  type        = map(string)
  description = "Optional tags to add to created resources"
}

variable "databricks_account_id" {}
variable "databricks_host" {}
variable "databricks_token" {}

variable "databricks_client_id" {}
variable "databricks_client_secret" {}
variable "databricks_workspace_id" {}

variable "region" {
  default = "ap-southeast-2"
}

# Include the aws_session_token if the temporary credential is used
variable "aws_session_token" {
  description = "AWS session token"
  type        = string
  default     = null
}

variable "aws_access_key" {
  description = "AWS Access Key"
  type        = string
  default     = null
}
variable "aws_secret_key" {
  description = "AWS secret Key"
  type        = string
  default     = null
}
variable "aws_account_id" {}

variable "catalog_1" {
  default = "prod"
}

variable "catalog_2" {
  default = "dev"
}

variable "catalog_3" {
  default = "sandbox"
}

variable "group_1" {
  default = "production_sp"
}

variable "group_2" {
  default = "developers"
}

variable "group_3" {
  default = "sandbox_users"
}



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