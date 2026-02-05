# ============================================================================
# Outputs for Finance ABAC Account Groups
# ============================================================================

output "finance_group_ids" {
  description = "Map of group names to their Databricks group IDs"
  value = {
    for name, group in databricks_group.finance_groups : name => group.id
  }
}

output "finance_group_names" {
  description = "List of all created finance group names"
  value       = keys(databricks_group.finance_groups)
}

# ----------------------------------------------------------------------------
# Compliance Framework Mapping
# ----------------------------------------------------------------------------

output "compliance_framework_groups" {
  description = "Groups organized by compliance framework"
  value = {
    "PCI-DSS" = [
      "Credit_Card_Support",
      "Fraud_Analyst"
    ]
    "AML-KYC" = [
      "AML_Investigator_Junior",
      "AML_Investigator_Senior",
      "Compliance_Officer"
    ]
    "SEC-MiFID-II" = [
      "Equity_Trader",
      "Fixed_Income_Trader",
      "Research_Analyst",
      "Risk_Manager"
    ]
    "GDPR-CCPA" = [
      "Regional_EU_Staff",
      "Regional_US_Staff",
      "Regional_APAC_Staff",
      "Marketing_Team"
    ]
    "SOX" = [
      "External_Auditor",
      "Compliance_Officer"
    ]
    "GLBA" = [
      "KYC_Specialist",
      "Credit_Card_Support"
    ]
  }
}

# ----------------------------------------------------------------------------
# Workspace Assignment and Entitlements
# ----------------------------------------------------------------------------

output "workspace_assignments" {
  description = "Map of group names to their workspace assignment IDs"
  value = {
    for name, assignment in databricks_mws_permission_assignment.finance_group_assignments : name => assignment.id
  }
}

output "group_entitlements" {
  description = "Summary of entitlements granted to each group"
  value = {
    for name, entitlement in databricks_entitlements.finance_group_entitlements : name => {
      workspace_consume = entitlement.workspace_consume
    }
  }
}
