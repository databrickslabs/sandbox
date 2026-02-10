# ============================================================================
# Variables for Finance ABAC Account Groups
# ============================================================================

variable "databricks_account_id" {
  type        = string
  description = "The Databricks account ID"
}

variable "databricks_client_id" {
  type        = string
  description = "The Databricks service principal client ID for authentication"
}

variable "databricks_client_secret" {
  type        = string
  description = "The Databricks service principal client secret for authentication"
  sensitive   = true
}

variable "databricks_workspace_id" {
  type        = string
  description = "The Databricks workspace ID where the groups will be assigned"
}

variable "databricks_workspace_host" {
  type        = string
  description = "The Databricks workspace URL (e.g., https://myworkspace.cloud.databricks.com)"
}

# ----------------------------------------------------------------------------
# Demo user assignments (optional)
# ----------------------------------------------------------------------------
# Account-level user IDs for adding users to groups. Leave empty to skip.
# Get IDs from Account Console > Users or SCIM API.

variable "demo_user_junior_us_id" {
  type        = string
  default     = ""
  description = "Account-level user ID for kavya.parashar@databricks.com (added to Junior_Analyst and US_Region_Staff). Leave empty to skip."
}

variable "demo_user_senior_eu_id" {
  type        = string
  default     = ""
  description = "Account-level user ID for louis.chen@databricks.com (added to Senior_Analyst and EU_Region_Staff). Leave empty to skip."
}

# ----------------------------------------------------------------------------
# Genie Space: warehouse and data access
# ----------------------------------------------------------------------------

variable "genie_warehouse_name" {
  type        = string
  default     = "Genie Finance Warehouse"
  description = "Name of the serverless SQL warehouse created for Genie (used only when genie_use_existing_warehouse_id is empty)."
}

variable "genie_use_existing_warehouse_id" {
  type        = string
  default     = ""
  description = "When set, do not create a new warehouse; use this ID for permissions and for genie_space.sh create. When empty, Terraform creates a serverless warehouse."
}

variable "genie_default_warehouse_id" {
  type        = string
  default     = ""
  description = "Deprecated: use genie_use_existing_warehouse_id. SQL warehouse ID when not creating one in Terraform."
}

variable "uc_catalog_name" {
  type        = string
  default     = "fincat"
  description = "Unity Catalog catalog name used by the Genie Space (for USE_CATALOG, USE_SCHEMA, SELECT grants)."
}

variable "uc_schema_name" {
  type        = string
  default     = "finance"
  description = "Unity Catalog schema name used by the Genie Space (for USE_SCHEMA, SELECT grants)."
}
