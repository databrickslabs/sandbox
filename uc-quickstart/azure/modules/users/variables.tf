variable "databricks_account_id" {
  type        = string
  description = "The Databricks account ID"
}

variable "azure_client_id" {
  type        = string
  description = "Azure client ID for authentication"
}

variable "azure_client_secret" {
  type        = string
  description = "Azure client secret for authentication"
  sensitive   = true
}

variable "group_name" {
  type        = string
  description = "Name of the user group to create"
}

variable "databricks_workspace_id" {
  type        = string
  description = "The Databricks workspace ID where the group will be created"
}

variable "azure_tenant_id" {
  type        = string
  description = "Azure tenant ID for authentication"
}