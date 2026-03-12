# ============================================================================
# Group Memberships (data-driven)
# ============================================================================
# Adds users to groups based on var.group_members.
# Map of group name -> list of account-level user IDs.
# ============================================================================

locals {
  group_member_pairs = flatten([
    for group, members in var.group_members : [
      for member_id in members : {
        group     = group
        member_id = member_id
      }
    ]
  ])

  group_member_map = {
    for pair in local.group_member_pairs :
    "${pair.group}|${pair.member_id}" => pair
  }
}

resource "databricks_group_member" "members" {
  for_each = local.group_member_map

  provider  = databricks.account
  group_id  = databricks_group.groups[each.value.group].id
  member_id = each.value.member_id

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
  ]
}
