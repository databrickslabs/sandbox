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

  # Column mask policies: match_columns + column_mask
  dynamic "match_columns" {
    for_each = each.value.policy_type == "POLICY_TYPE_COLUMN_MASK" ? [1] : []
    content {
      condition = each.value.match_condition
      alias     = each.value.match_alias
    }
  }

  dynamic "column_mask" {
    for_each = each.value.policy_type == "POLICY_TYPE_COLUMN_MASK" ? [1] : []
    content {
      function_name = "${var.uc_catalog_name}.${var.uc_schema_name}.${each.value.function_name}"
      on_column     = each.value.match_alias
      using         = []
    }
  }

  # Row filter policies: when_condition + row_filter
  when_condition = each.value.policy_type == "POLICY_TYPE_ROW_FILTER" ? each.value.when_condition : null

  dynamic "row_filter" {
    for_each = each.value.policy_type == "POLICY_TYPE_ROW_FILTER" ? [1] : []
    content {
      function_name = "${var.uc_catalog_name}.${var.uc_schema_name}.${each.value.function_name}"
      using         = []
    }
  }

  depends_on = [
    databricks_tag_policy.policies,
    databricks_entity_tag_assignment.assignments,
    databricks_mws_permission_assignment.group_assignments,
    databricks_grant.catalog_access,
    databricks_grant.terraform_sp_manage_catalog,
  ]
}
