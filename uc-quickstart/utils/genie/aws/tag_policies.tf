# ============================================================================
# Unity Catalog Tag Policies for Minimal Finance ABAC Demo (5 Scenarios)
# ============================================================================
# Governed tag policies used by ABAC. Tag policies must exist before applying
# tags in SQL (3.ApplyFinanceSetTags.sql) and before creating ABAC policies.
#
# NOTE: If your Databricks provider does not include the tag_policy resource,
# comment out or remove this file and create tag policies via REST API or
# run abac/finance/2.CreateFinanceTagPolicies.py (reduced to these 5 keys).
# ============================================================================

# Tag policy: AML clearance (Scenario 3 - transaction amount rounding)
resource "databricks_tag_policy" "aml_clearance" {
  provider    = databricks.workspace
  tag_key     = "aml_clearance"
  description = "AML investigation clearance for minimal demo: Junior_Analyst, Senior_Investigator, Compliance_Officer"
  values = [
    { name = "Junior_Analyst" },
    { name = "Senior_Investigator" },
    { name = "Compliance_Officer" }
  ]

  lifecycle {
    ignore_changes = [values]
  }
}

# Tag policy: PII level (Scenario 1 - PII masking on Customers)
resource "databricks_tag_policy" "pii_level" {
  provider    = databricks.workspace
  depends_on  = [databricks_tag_policy.aml_clearance]
  tag_key     = "pii_level"
  description = "PII access level for minimal demo: Limited_PII (junior), Full_PII (senior/compliance)"
  values = [
    { name = "Limited_PII" },
    { name = "Full_PII" }
  ]

  lifecycle {
    ignore_changes = [values]
  }
}

# Tag policy: PCI clearance (Scenario 2 - Credit card masking)
resource "databricks_tag_policy" "pci_clearance" {
  provider    = databricks.workspace
  depends_on  = [databricks_tag_policy.pii_level]
  tag_key     = "pci_clearance"
  description = "PCI-DSS clearance for minimal demo: Basic (last4), Full (full card), Administrative (full+CVV)"
  values = [
    { name = "Basic" },
    { name = "Full" },
    { name = "Administrative" }
  ]

  lifecycle {
    ignore_changes = [values]
  }
}

# Tag policy: Customer region (Scenarios 4 & 5 - row filters)
resource "databricks_tag_policy" "customer_region" {
  provider    = databricks.workspace
  depends_on  = [databricks_tag_policy.pci_clearance]
  tag_key     = "customer_region"
  description = "Customer data region for minimal demo: Regional (table in scope), US, EU"
  values = [
    { name = "Regional" },
    { name = "US" },
    { name = "EU" }
  ]

  lifecycle {
    ignore_changes = [values]
  }
}

# Tag policy: Data residency (Scenarios 4 & 5 - row filters)
resource "databricks_tag_policy" "data_residency" {
  provider    = databricks.workspace
  depends_on  = [databricks_tag_policy.customer_region]
  tag_key     = "data_residency"
  description = "Data residency for minimal demo: Global, US, EU"
  values = [
    { name = "Global" },
    { name = "US" },
    { name = "EU" }
  ]

  lifecycle {
    ignore_changes = [values]
  }
}
