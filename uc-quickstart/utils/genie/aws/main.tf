# ============================================================================
# Finance ABAC Account Groups - Terraform Configuration (Minimal 5-Group Demo)
# ============================================================================
# This module creates account-level user groups for the minimal finance ABAC
# demo in Databricks Unity Catalog.
#
# Groups Created (5 Total):
# - Junior_Analyst: Masked PII, last-4 card only, rounded transaction amounts
# - Senior_Analyst: Unmasked PII, full card number, full transaction details
# - US_Region_Staff: Row access limited to CustomerRegion = 'US'
# - EU_Region_Staff: Row access limited to CustomerRegion = 'EU'
# - Compliance_Officer: Full unmasked access (all regions, all columns)
# ============================================================================

locals {
  finance_groups = {
    "Junior_Analyst" = {
      display_name = "Junior Analyst"
      description  = "Junior analysts with masked PII, last-4 card only, rounded transaction amounts"
    }
    "Senior_Analyst" = {
      display_name = "Senior Analyst"
      description  = "Senior analysts with unmasked PII, full card number, full transaction details"
    }
    "US_Region_Staff" = {
      display_name = "US Region Staff"
      description  = "Staff with row access limited to US customer data (GLBA, CCPA)"
    }
    "EU_Region_Staff" = {
      display_name = "EU Region Staff"
      description  = "Staff with row access limited to EU customer data (GDPR)"
    }
    "Compliance_Officer" = {
      display_name = "Compliance Officer"
      description  = "Full unmasked access to all regions and columns for audit"
    }
  }
}

# ----------------------------------------------------------------------------
# Create Account-Level Groups
# ----------------------------------------------------------------------------
# These groups are created at the Databricks account level and are available
# across all workspaces in the account.

resource "databricks_group" "finance_groups" {
  for_each = local.finance_groups

  provider     = databricks.account
  display_name = each.key

  # Note: Databricks groups don't have a native description field via Terraform
  # The description is maintained in the locals block for documentation purposes
}

# ----------------------------------------------------------------------------
# Assign Groups to Workspace
# ----------------------------------------------------------------------------
# Assigns the account-level groups to the specified workspace with USER permissions

resource "databricks_mws_permission_assignment" "finance_group_assignments" {
  for_each = databricks_group.finance_groups

  provider     = databricks.account
  workspace_id = var.databricks_workspace_id
  principal_id = each.value.id
  permissions  = ["USER"]
}

# ----------------------------------------------------------------------------
# Grant Consumer Entitlements to Groups (Databricks One UI only)
# ----------------------------------------------------------------------------
# These groups get ONLY consumer access: Databricks One UI (Genie, dashboards,
# apps). They do NOT get full workspace UI (clusters, notebooks, SQL workspace).
# workspace_consume cannot be used with workspace_access or databricks_sql_access.
#
# Reference: https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/entitlements

resource "databricks_entitlements" "finance_group_entitlements" {
  for_each = databricks_group.finance_groups

  provider = databricks.workspace
  group_id = each.value.id

  # Consumer only: One UI (Genie, dashboards, apps). No full workspace or SQL UI.
  # Do not add workspace_access, databricks_sql_access, or allow_cluster_create (conflicts with workspace_consume).
  workspace_consume = true

  depends_on = [databricks_mws_permission_assignment.finance_group_assignments]
}
