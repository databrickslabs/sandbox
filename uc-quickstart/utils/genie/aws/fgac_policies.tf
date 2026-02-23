# ============================================================================
# FGAC Policies (data-driven)
# ============================================================================
# Creates catalog-level ABAC policies from var.fgac_policies.
# Supports both POLICY_TYPE_COLUMN_MASK and POLICY_TYPE_ROW_FILTER.
#
# Prerequisites:
# - Tag policies and entity tag assignments applied
# - Masking / filter UDFs deployed in the target catalog.schema
# - Groups assigned to the workspace
# ============================================================================

locals {
  fgac_policy_map = { for p in var.fgac_policies : p.name => p }
}

resource "time_sleep" "wait_for_tag_propagation" {
  depends_on      = [databricks_tag_policy.policies, databricks_entity_tag_assignment.assignments]
  create_duration = "10s"
}

resource "databricks_policy_info" "policies" {
  for_each = local.fgac_policy_map

  provider = databricks.workspace

  name                  = "${var.uc_catalog_name}_${each.key}"
  on_securable_type     = "CATALOG"
  on_securable_fullname = var.uc_catalog_name
  policy_type           = each.value.policy_type
  for_securable_type    = "TABLE"
  to_principals         = each.value.to_principals
  except_principals     = length(each.value.except_principals) > 0 ? each.value.except_principals : null
  comment               = each.value.comment

  when_condition = (
    each.value.policy_type == "POLICY_TYPE_COLUMN_MASK"
    ? each.value.match_condition
    : each.value.when_condition
  )

  match_columns = each.value.policy_type == "POLICY_TYPE_COLUMN_MASK" ? [{
    condition = each.value.match_condition
    alias     = each.value.match_alias
  }] : null

  column_mask = each.value.policy_type == "POLICY_TYPE_COLUMN_MASK" ? {
    function_name = "${var.uc_catalog_name}.${var.uc_schema_name}.${each.value.function_name}"
    on_column     = each.value.match_alias
    using         = []
  } : null

  row_filter = each.value.policy_type == "POLICY_TYPE_ROW_FILTER" ? {
    function_name = "${var.uc_catalog_name}.${var.uc_schema_name}.${each.value.function_name}"
    using         = []
  } : null

  depends_on = [
    time_sleep.wait_for_tag_propagation,
    databricks_mws_permission_assignment.group_assignments,
    databricks_grant.catalog_access,
    databricks_grant.terraform_sp_manage_catalog,
  ]
}
