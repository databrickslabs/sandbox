# ============================================================================
# Variables for Generic ABAC Terraform Module
# ============================================================================

# ----------------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------------

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
# Unity Catalog tables (used by generate_abac.py only)
# ----------------------------------------------------------------------------

variable "uc_tables" {
  type        = list(string)
  default     = []
  description = "Tables to generate ABAC policies for. Used by generate_abac.py only; ignored by Terraform."
}

# ----------------------------------------------------------------------------
# SQL warehouse for deploying masking functions
# ----------------------------------------------------------------------------

variable "sql_warehouse_id" {
  type        = string
  default     = ""
  description = "SQL warehouse ID for deploying masking functions. When set, masking_functions.sql is executed automatically during terraform apply. When empty, masking functions must be deployed manually."
}

# ----------------------------------------------------------------------------
# Groups
# ----------------------------------------------------------------------------

variable "groups" {
  type = map(object({
    description = optional(string, "")
  }))
  description = "Map of group name -> config. Each key becomes an account-level databricks_group, assigned to the workspace with consumer entitlements."
}

# ----------------------------------------------------------------------------
# Group members (optional)
# ----------------------------------------------------------------------------

variable "group_members" {
  type        = map(list(string))
  default     = {}
  description = "Map of group name -> list of account-level user IDs. Adds users to the corresponding group. Get IDs from Account Console > Users or SCIM API."
}

# ----------------------------------------------------------------------------
# Tag policies
# ----------------------------------------------------------------------------

variable "tag_policies" {
  type = list(object({
    key         = string
    description = optional(string, "")
    values      = list(string)
  }))
  default     = []
  description = "Tag policies to create. Each becomes a databricks_tag_policy with governed allowed values."
}

# ----------------------------------------------------------------------------
# Tag assignments
# ----------------------------------------------------------------------------

variable "tag_assignments" {
  type = list(object({
    entity_type = string
    entity_name = string
    tag_key     = string
    tag_value   = string
  }))
  default     = []
  description = "Tag-to-entity mappings. entity_type is 'tables' or 'columns'. entity_name must be fully qualified (catalog.schema.table for tables, catalog.schema.table.column for columns)."
}

# ----------------------------------------------------------------------------
# FGAC policies
# ----------------------------------------------------------------------------

variable "fgac_policies" {
  type = list(object({
    name              = string
    policy_type       = string
    catalog           = string
    to_principals     = list(string)
    except_principals = optional(list(string), [])
    comment           = optional(string, "")
    match_condition   = optional(string)
    match_alias       = optional(string)
    function_name     = string
    function_catalog  = string
    function_schema   = string
    when_condition    = optional(string)
  }))
  default     = []
  description = "FGAC policies. catalog: which catalog the policy is scoped to. function_catalog/function_schema: where the masking UDF lives. function_name: relative UDF name (e.g. 'mask_pii_partial')."
}

# ----------------------------------------------------------------------------
# Genie Space: warehouse and data access
# ----------------------------------------------------------------------------

variable "genie_warehouse_name" {
  type        = string
  default     = "Genie ABAC Warehouse"
  description = "Name of the serverless SQL warehouse created for Genie (used only when genie_use_existing_warehouse_id is empty)."
}

variable "genie_use_existing_warehouse_id" {
  type        = string
  default     = ""
  description = "When set, do not create a new warehouse; use this ID for genie_space.sh create. When empty, Terraform creates a serverless warehouse."
}

variable "genie_default_warehouse_id" {
  type        = string
  default     = ""
  description = "Deprecated: use genie_use_existing_warehouse_id."
}

variable "genie_space_id" {
  type        = string
  default     = ""
  description = "Genie Space ID for setting ACLs. When set, Terraform runs set-acls using SP credentials to grant CAN_RUN to all configured groups."
}
