# ============================================================================
# Demo User Group Memberships (Minimal Finance ABAC Demo)
# ============================================================================
# Adds demo users to the 5 finance groups. Uses account-level group membership.
# Set demo_user_junior_us_id and demo_user_senior_eu_id in tfvars to enable.
# ============================================================================

# kavya.parashar@databricks.com -> Junior_Analyst and US_Region_Staff
resource "databricks_group_member" "kavya_junior_analyst" {
  count = var.demo_user_junior_us_id != "" ? 1 : 0

  provider  = databricks.account
  group_id  = databricks_group.finance_groups["Junior_Analyst"].id
  member_id = var.demo_user_junior_us_id
}

resource "databricks_group_member" "kavya_us_region_staff" {
  count = var.demo_user_junior_us_id != "" ? 1 : 0

  provider  = databricks.account
  group_id  = databricks_group.finance_groups["US_Region_Staff"].id
  member_id = var.demo_user_junior_us_id
}

# louis.chen@databricks.com -> Senior_Analyst and EU_Region_Staff
resource "databricks_group_member" "louis_senior_analyst" {
  count = var.demo_user_senior_eu_id != "" ? 1 : 0

  provider  = databricks.account
  group_id  = databricks_group.finance_groups["Senior_Analyst"].id
  member_id = var.demo_user_senior_eu_id
}

resource "databricks_group_member" "louis_eu_region_staff" {
  count = var.demo_user_senior_eu_id != "" ? 1 : 0

  provider  = databricks.account
  group_id  = databricks_group.finance_groups["EU_Region_Staff"].id
  member_id = var.demo_user_senior_eu_id
}
