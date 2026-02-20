# ============================================================================
# Finance ABAC Policies (from 4.CreateFinanceABACPolicies.sql)
# ============================================================================
# Catalog-level ABAC policies for the minimal finance demo (5 scenarios, 7 policies).
#
# Prerequisites (before applying this file):
# - Tag policies (tag_policies.tf) and entity tag assignments (entity_tag_assignments.tf)
# - ABAC UDFs deployed in the same catalog.schema (run 0.1finance_abac_functions.sql)
# - Tables created and tagged (0.2 schema + entity_tag_assignments or 3.ApplyFinanceSetTags.sql)
#
# Terraform resource: databricks_policy_info (Unity Catalog ABAC)
# https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/policy_info
# Requires Databricks Terraform provider that supports policy_info (check provider changelog).
# ============================================================================

locals {
  _cat  = var.uc_catalog_name
  _sch  = var.uc_schema_name
  _udf  = "${var.uc_catalog_name}.${var.uc_schema_name}"
}

# ----------------------------------------------------------------------------
# POLICY 1: PII Masking (Customers) - 2 policies
# Junior_Analyst: mask_pii_partial on Limited_PII columns, mask_ssn on SSN
# ----------------------------------------------------------------------------

resource "databricks_policy_info" "pii_junior_mask" {
  provider = databricks.workspace

  name                  = "${local._cat}_pii_junior_mask"
  depends_on = [
    databricks_tag_policy.aml_clearance,
    databricks_tag_policy.pii_level,
    databricks_tag_policy.pci_clearance,
    databricks_tag_policy.customer_region,
    databricks_tag_policy.data_residency,
    databricks_entity_tag_assignment.finance_abac,
    databricks_mws_permission_assignment.finance_group_assignments,
    databricks_grant.finance_catalog_access,
    databricks_grant.terraform_sp_manage_catalog,
  ]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_COLUMN_MASK"
  for_securable_type    = "TABLE"
  to_principals         = ["Junior_Analyst"]
  comment               = "PII: Mask names and email for junior analysts"

  match_columns = [
    { condition = "hasTagValue('pii_level', 'Limited_PII')", alias = "pii_cols" }
  ]
  column_mask = {
    function_name = "${local._udf}.mask_pii_partial"
    on_column     = "pii_cols"
    using         = []
  }
}

resource "databricks_policy_info" "pii_junior_ssn" {
  provider = databricks.workspace

  name                  = "${local._cat}_pii_junior_ssn"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_COLUMN_MASK"
  for_securable_type    = "TABLE"
  to_principals         = ["Junior_Analyst"]
  comment               = "PII: Mask SSN for junior analysts"

  match_columns = [
    { condition = "hasTagValue('pii_level', 'Full_PII') AND hasTagValue('data_residency', 'US')", alias = "ssn_cols" }
  ]
  column_mask = {
    function_name = "${local._udf}.mask_ssn"
    on_column     = "ssn_cols"
    using         = []
  }
}

# ----------------------------------------------------------------------------
# POLICY 2: Fraud / Card (CreditCards) - 2 policies
# Junior: last-4 only; Senior: full card (CVV masked); Compliance: full + CVV
# ----------------------------------------------------------------------------

resource "databricks_policy_info" "pci_junior_last4" {
  provider = databricks.workspace

  name                  = "${local._cat}_pci_junior_last4"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_COLUMN_MASK"
  for_securable_type    = "TABLE"
  to_principals         = ["Junior_Analyst"]
  comment               = "Card: Last 4 digits only for junior analysts"

  match_columns = [
    { condition = "hasTagValue('pci_clearance', 'Full')", alias = "card_cols" }
  ]
  column_mask = {
    function_name = "${local._udf}.mask_credit_card_last4"
    on_column     = "card_cols"
    using         = []
  }
}

resource "databricks_policy_info" "pci_cvv_mask_except_compliance" {
  provider = databricks.workspace

  name                  = "${local._cat}_pci_cvv_mask_except_compliance"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_COLUMN_MASK"
  for_securable_type    = "TABLE"
  to_principals         = ["account users"]
  except_principals     = ["Compliance_Officer"]
  comment               = "Card: Mask CVV for all except Compliance_Officer"

  match_columns = [
    { condition = "hasTagValue('pci_clearance', 'Administrative')", alias = "cvv_cols" }
  ]
  column_mask = {
    function_name = "${local._udf}.mask_credit_card_full"
    on_column     = "cvv_cols"
    using         = []
  }
}

# ----------------------------------------------------------------------------
# POLICY 3: Fraud / Transactions (Amount rounding)
# Junior_Analyst: rounded amounts; Senior + Compliance: full
# ----------------------------------------------------------------------------

resource "databricks_policy_info" "aml_junior_round" {
  provider = databricks.workspace

  name                  = "${local._cat}_aml_junior_round"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_COLUMN_MASK"
  for_securable_type    = "TABLE"
  to_principals         = ["Junior_Analyst"]
  comment               = "Transactions: Round amount for junior analysts"

  match_columns = [
    { condition = "hasTagValue('aml_clearance', 'Junior_Analyst')", alias = "aml_cols" }
  ]
  column_mask = {
    function_name = "${local._udf}.mask_amount_rounded"
    on_column     = "aml_cols"
    using         = []
  }
}

# ----------------------------------------------------------------------------
# POLICY 4: US Region (Row filter for US_Region_Staff)
# Tables tagged customer_region = 'Regional' get row filter for US staff
# ----------------------------------------------------------------------------

resource "databricks_policy_info" "region_us" {
  provider = databricks.workspace

  name                  = "${local._cat}_region_us"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_ROW_FILTER"
  for_securable_type    = "TABLE"
  to_principals         = ["US_Region_Staff"]
  comment               = "Region: US staff see US customer data only"
  when_condition        = "hasTagValue('customer_region', 'Regional')"

  row_filter = {
    function_name = "${local._udf}.filter_by_region_us"
    using         = []
  }
}

# ----------------------------------------------------------------------------
# POLICY 5: EU Region (Row filter for EU_Region_Staff)
# Tables tagged customer_region = 'Regional' get row filter for EU staff
# ----------------------------------------------------------------------------

resource "databricks_policy_info" "region_eu" {
  provider = databricks.workspace

  name                  = "${local._cat}_region_eu"
  depends_on            = [databricks_mws_permission_assignment.finance_group_assignments, databricks_grant.finance_catalog_access, databricks_grant.terraform_sp_manage_catalog]
  on_securable_type     = "CATALOG"
  on_securable_fullname = local._cat
  policy_type           = "POLICY_TYPE_ROW_FILTER"
  for_securable_type    = "TABLE"
  to_principals         = ["EU_Region_Staff"]
  comment               = "Region: EU staff see EU customer data only"
  when_condition        = "hasTagValue('customer_region', 'Regional')"

  row_filter = {
    function_name = "${local._udf}.filter_by_region_eu"
    using         = []
  }
}
