# ============================================================================
# Finance ABAC Account Groups - Terraform Configuration
# ============================================================================
# This module creates account-level user groups for finance ABAC scenarios
# in Databricks Unity Catalog.
#
# Groups Created (15 Total):
# - PCI-DSS: Credit_Card_Support, Fraud_Analyst
# - AML/KYC: AML_Investigator_Junior, AML_Investigator_Senior, Compliance_Officer
# - Trading: Equity_Trader, Fixed_Income_Trader, Research_Analyst, Risk_Manager
# - Privacy: Regional_EU_Staff, Regional_US_Staff, Regional_APAC_Staff, Marketing_Team
# - Audit: External_Auditor, KYC_Specialist
# ============================================================================

locals {
  # Define all finance user groups with their metadata
  finance_groups = {
    "Credit_Card_Support" = {
      display_name = "Credit Card Support"
      description  = "Customer service representatives handling credit card inquiries (PCI-DSS Basic access)"
    }
    "Fraud_Analyst" = {
      display_name = "Fraud Analyst"
      description  = "Fraud detection analysts with full access to payment card data (PCI-DSS Full access)"
    }
    "AML_Investigator_Junior" = {
      display_name = "AML Investigator Junior"
      description  = "Junior AML analysts with limited access to transaction data"
    }
    "AML_Investigator_Senior" = {
      display_name = "AML Investigator Senior"
      description  = "Senior AML investigators with enhanced access to customer and transaction data"
    }
    "Compliance_Officer" = {
      display_name = "Compliance Officer"
      description  = "Regulatory compliance officers with comprehensive access to all compliance data"
    }
    "Equity_Trader" = {
      display_name = "Equity Trader"
      description  = "Equity trading desk staff with access to equity positions"
    }
    "Fixed_Income_Trader" = {
      display_name = "Fixed Income Trader"
      description  = "Fixed income trading desk staff with access to bond and treasury positions"
    }
    "Research_Analyst" = {
      display_name = "Research Analyst"
      description  = "Research and advisory team separated by Chinese wall from trading"
    }
    "Risk_Manager" = {
      display_name = "Risk Manager"
      description  = "Risk management team with neutral access across trading desks"
    }
    "External_Auditor" = {
      display_name = "External Auditor"
      description  = "External auditors with temporary, time-limited access to financial records"
    }
    "Marketing_Team" = {
      display_name = "Marketing Team"
      description  = "Marketing team with de-identified customer data access"
    }
    "KYC_Specialist" = {
      display_name = "KYC Specialist"
      description  = "Know Your Customer specialists with full PII access for verification"
    }
    "Regional_EU_Staff" = {
      display_name = "Regional EU Staff"
      description  = "Staff based in European Union with access to EU customer data only (GDPR)"
    }
    "Regional_US_Staff" = {
      display_name = "Regional US Staff"
      description  = "Staff based in United States with access to US customer data (GLBA, CCPA)"
    }
    "Regional_APAC_Staff" = {
      display_name = "Regional APAC Staff"
      description  = "Staff based in Asia-Pacific region with access to APAC customer data"
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
# Grant Consumer Entitlements to Groups
# ----------------------------------------------------------------------------
# Grants minimal consumer entitlement following least privilege principle:
# - workspace_consume: Minimal consumer access to workspace (can access but not create resources)
#
# Reference: https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/entitlements

resource "databricks_entitlements" "finance_group_entitlements" {
  for_each = databricks_group.finance_groups

  provider = databricks.workspace
  group_id = each.value.id

  # Minimal consumer entitlement
  workspace_consume = true

  depends_on = [databricks_mws_permission_assignment.finance_group_assignments]
}
