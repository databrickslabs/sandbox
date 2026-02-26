# ============================================================================
# Unity Catalog Tag Policies (data-driven)
# ============================================================================
# Creates governed tag policies from var.tag_policies. Each entry defines a
# tag key and its allowed values. Tag policies must exist before tags can be
# assigned to entities and before FGAC policies can reference them.
#
# NOTE: The Databricks provider has a known bug where the API reorders tag
# policy values after creation, causing "Provider produced inconsistent result
# after apply". The lifecycle block below suppresses value-ordering drift.
# On first apply the error is expected; `make apply` auto-imports the
# policies and retries cleanly.
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
