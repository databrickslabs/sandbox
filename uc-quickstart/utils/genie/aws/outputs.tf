# ============================================================================
# Outputs
# ============================================================================

output "group_ids" {
  description = "Map of group names to their Databricks group IDs"
  value = {
    for name, group in databricks_group.groups : name => group.id
  }
}

output "group_names" {
  description = "List of all created group names"
  value       = keys(databricks_group.groups)
}

output "workspace_assignments" {
  description = "Map of group names to their workspace assignment IDs"
  value = {
    for name, assignment in databricks_mws_permission_assignment.group_assignments : name => assignment.id
  }
}

output "group_entitlements" {
  description = "Summary of entitlements granted to each group"
  value = {
    for name, entitlement in databricks_entitlements.group_entitlements : name => {
      workspace_consume = entitlement.workspace_consume
    }
  }
}

# ----------------------------------------------------------------------------
# SQL warehouse (provided or auto-created)
# ----------------------------------------------------------------------------

output "sql_warehouse_id" {
  description = "Effective SQL warehouse ID (user-provided or auto-created)."
  value       = local.effective_warehouse_id
}

output "genie_space_acls_applied" {
  description = "Whether Genie Space ACLs were applied (existing or newly created space)"
  value       = length(null_resource.genie_space_acls) > 0 || length(null_resource.genie_space_create) > 0
}

output "genie_space_acls_groups" {
  description = "Groups that were granted CAN_RUN on the Genie Space"
  value = (
    length(null_resource.genie_space_acls) > 0 || length(null_resource.genie_space_create) > 0
    ? keys(var.groups)
    : []
  )
}

output "genie_space_created" {
  description = "Whether a new Genie Space was auto-created by Terraform"
  value       = length(null_resource.genie_space_create) > 0
}

output "genie_groups_csv" {
  description = "Comma-separated group names for genie_space.sh"
  value       = join(",", keys(var.groups))
}
