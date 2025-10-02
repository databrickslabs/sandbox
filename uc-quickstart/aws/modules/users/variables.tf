variable "group_name" {
  type        = string
  description = "Name of the user group to create"
}

variable "databricks_workspace_id" {
  type        = string
  description = "The Databricks workspace ID where the group will be created"
}