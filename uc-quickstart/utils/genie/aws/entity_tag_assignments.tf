# ============================================================================
# Entity Tag Assignments (data-driven)
# ============================================================================
# Applies governed tags to tables and columns from var.tag_assignments.
# entity_name must be fully qualified (catalog.schema.table for tables,
# catalog.schema.table.column for columns).
# ============================================================================

locals {
  tag_assignment_map = {
    for ta in var.tag_assignments :
    "${ta.entity_type}|${ta.entity_name}|${ta.tag_key}|${ta.tag_value}" => ta
  }
}

resource "databricks_entity_tag_assignment" "assignments" {
  for_each = local.tag_assignment_map

  provider    = databricks.workspace
  entity_type = each.value.entity_type
  entity_name = each.value.entity_name
  tag_key     = each.value.tag_key
  tag_value   = each.value.tag_value

  depends_on = [databricks_tag_policy.policies]
}
