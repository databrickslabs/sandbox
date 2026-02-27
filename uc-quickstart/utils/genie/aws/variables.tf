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
# SQL warehouse (shared by masking function deployment + Genie Space)
# ----------------------------------------------------------------------------

variable "sql_warehouse_id" {
  type        = string
  default     = ""
  description = "Existing SQL warehouse ID. When set, reused for masking function deployment and Genie Space. When empty, Terraform auto-creates a serverless warehouse."
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
# Genie Space
# ----------------------------------------------------------------------------

variable "warehouse_name" {
  type        = string
  default     = "ABAC Serverless Warehouse"
  description = "Name of the auto-created serverless warehouse (only used when sql_warehouse_id is empty)."
}

variable "genie_space_id" {
  type        = string
  default     = ""
  description = "Existing Genie Space ID. When set, Terraform applies CAN_RUN ACLs for configured groups. When empty and uc_tables is non-empty, Terraform auto-creates a new Genie Space."
}

variable "genie_space_title" {
  type        = string
  default     = "One Ready Genie Space"
  description = "Title for the auto-created Genie Space (only used when genie_space_id is empty)."
}

variable "genie_space_description" {
  type        = string
  default     = ""
  description = "Optional description for the auto-created Genie Space (only used when genie_space_id is empty)."
}

variable "genie_sample_questions" {
  type        = list(string)
  default     = []
  description = "Sample questions shown to users in the Genie Space UI. Auto-generated by generate_abac.py if not set."
}

variable "genie_instructions" {
  type        = string
  default     = ""
  description = "Text instructions for the Genie Space LLM (e.g., domain-specific guidance, calculation rules)."
}

variable "genie_benchmarks" {
  type = list(object({
    question = string
    sql      = string
  }))
  default     = []
  description = "Benchmark questions with ground-truth SQL for evaluating Genie Space accuracy."
}

variable "genie_sql_filters" {
  type = list(object({
    sql          = string
    display_name = string
    comment      = string
    instruction  = string
  }))
  default     = []
  description = "SQL snippet filters for the Genie Space (e.g., default WHERE clauses like active customers, completed transactions)."
}

variable "genie_sql_expressions" {
  type = list(object({
    alias        = string
    sql          = string
    display_name = string
    comment      = string
    instruction  = string
  }))
  default     = []
  description = "SQL snippet expressions/dimensions for the Genie Space (e.g., transaction year, age bucket)."
}

variable "genie_sql_measures" {
  type = list(object({
    alias        = string
    sql          = string
    display_name = string
    comment      = string
    instruction  = string
  }))
  default     = []
  description = "SQL snippet measures/aggregations for the Genie Space (e.g., total revenue, average risk score)."
}

variable "genie_join_specs" {
  type = list(object({
    left_table  = string
    left_alias  = string
    right_table = string
    right_alias = string
    sql         = string
    comment     = string
    instruction = string
  }))
  default     = []
  description = "Join specifications between tables for the Genie Space (e.g., accounts to customers on CustomerID)."
}
