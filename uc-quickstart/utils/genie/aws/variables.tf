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

variable "genie_default_warehouse_id" {
  type        = string
  default     = ""
  description = "SQL warehouse ID designated for the Genie Space. When set, CAN_USE is granted to the five groups. Required for Genie if consumers run queries."
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
