output "group_id" {
  description = "ID of the created Databricks group"
  value       = databricks_group.account_group.id
}

output "group_name" {
  description = "Name of the created Databricks group"
  value       = databricks_group.account_group.display_name
}
