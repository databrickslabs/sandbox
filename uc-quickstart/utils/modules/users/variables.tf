variable "group_name" {
  type        = string
  description = "Name of the user group to create"
}

variable "databricks_account_id" {
  type        = string
  description = "The Databricks account ID"
}

variable "databricks_workspace_id" {
  type        = string
  description = "The Databricks workspace ID where the group will be created"
}

# Cloud-specific authentication variables (optional)
variable "azure_client_id" {
  type        = string
  description = "Azure client ID for authentication (Azure only)"
  default     = null
}

variable "azure_client_secret" {
  type        = string
  description = "Azure client secret for authentication (Azure only)"
  default     = null
  sensitive   = true
}

variable "azure_tenant_id" {
  type        = string
  description = "Azure tenant ID for authentication (Azure only)"
  default     = null
}
