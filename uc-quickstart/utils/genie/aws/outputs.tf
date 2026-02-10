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
# Minimal Demo Scenario Mapping (5 groups, 5 scenarios)
# ----------------------------------------------------------------------------

output "demo_scenario_groups" {
  description = "Groups mapped to minimal ABAC demo scenarios"
  value = {
    "1_PII_masking"       = ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"]
    "2_Fraud_card"        = ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"]
    "3_Fraud_transactions" = ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"]
    "4_US_region"         = ["US_Region_Staff"]
    "5_EU_region"         = ["EU_Region_Staff"]
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

# ----------------------------------------------------------------------------
# Genie: warehouse for genie_space.sh create
# ----------------------------------------------------------------------------

output "genie_warehouse_id" {
  description = "SQL warehouse ID for the Genie Space (created or existing). Pass to scripts/genie_space.sh create as GENIE_WAREHOUSE_ID."
  value       = local.genie_warehouse_id
}
