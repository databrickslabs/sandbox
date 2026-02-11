# ============================================================================
# Demo User Group Memberships (Minimal Finance ABAC Demo)
# ============================================================================
# Adds demo users to the 5 finance groups. Uses account-level group membership.
# Set demo_user_junior_us_ids and demo_user_senior_eu_ids in tfvars to enable.
# ============================================================================

# Each ID in demo_user_junior_us_ids -> Junior_Analyst and US_Region_Staff
resource "databricks_group_member" "junior_analyst_demo" {
  for_each = toset(var.demo_user_junior_us_ids)

  provider   = databricks.account
  group_id   = databricks_group.finance_groups["Junior_Analyst"].id
  member_id  = each.value
  depends_on = [databricks_group.finance_groups, databricks_mws_permission_assignment.finance_group_assignments]
}

resource "databricks_group_member" "us_region_staff_demo" {
  for_each = toset(var.demo_user_junior_us_ids)

  provider   = databricks.account
  group_id   = databricks_group.finance_groups["US_Region_Staff"].id
  member_id  = each.value
  depends_on = [databricks_group.finance_groups, databricks_mws_permission_assignment.finance_group_assignments]
}

# Each ID in demo_user_senior_eu_ids -> Senior_Analyst and EU_Region_Staff
resource "databricks_group_member" "senior_analyst_demo" {
  for_each = toset(var.demo_user_senior_eu_ids)

  provider   = databricks.account
  group_id   = databricks_group.finance_groups["Senior_Analyst"].id
  member_id  = each.value
  depends_on = [databricks_group.finance_groups, databricks_mws_permission_assignment.finance_group_assignments]
}

resource "databricks_group_member" "eu_region_staff_demo" {
  for_each = toset(var.demo_user_senior_eu_ids)

  provider   = databricks.account
  group_id   = databricks_group.finance_groups["EU_Region_Staff"].id
  member_id  = each.value
  depends_on = [databricks_group.finance_groups, databricks_mws_permission_assignment.finance_group_assignments]
}
