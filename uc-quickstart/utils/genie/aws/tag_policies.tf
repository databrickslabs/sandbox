# ============================================================================
# Unity Catalog Tag Policies (data-driven)
# ============================================================================
# Creates governed tag policies from var.tag_policies. Each entry defines a
# tag key and its allowed values. Tag policies must exist before tags can be
# assigned to entities and before FGAC policies can reference them.
#
# IMPORTANT: ignore_changes on values is required because the Databricks
# provider has a bug where it reorders tag policy values after apply, causing
# "Provider produced inconsistent result" errors. Tag policy value updates
# are handled externally by `make sync-tags` (which calls the Databricks
# SDK to update values before terraform apply).
# ============================================================================

resource "databricks_tag_policy" "policies" {
  for_each = { for tp in var.tag_policies : tp.key => tp }

  provider    = databricks.workspace
  tag_key     = each.value.key
  description = each.value.description
  values      = [for v in each.value.values : { name = v }]

  lifecycle {
    ignore_changes = [values]
  }
}
