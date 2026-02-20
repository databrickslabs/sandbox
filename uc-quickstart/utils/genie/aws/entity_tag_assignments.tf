# ============================================================================
# Finance ABAC Tag Assignments (from 3.ApplyFinanceSetTags.sql)
# ============================================================================
# Applies governed tags to tables and columns for the 5 ABAC scenarios.
# Requires tag policies (tag_policies.tf) and tables to exist in UC.
# Uses databricks_entity_tag_assignment:
#   https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/entity_tag_assignment
# ============================================================================

locals {
  _c = var.uc_catalog_name
  _s = var.uc_schema_name

  # Flattened list of { entity_type, entity_name, tag_key, tag_value } for for_each
  # Key must be unique: entity_type|entity_name|tag_key|tag_value
  finance_tag_assignments = {
    # ---- SCENARIO 1: PII (Customers) ----
    "tables|${local._c}.${local._s}.Customers|data_residency|Global" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Customers"
      tag_key     = "data_residency"
      tag_value   = "Global"
    }
    "tables|${local._c}.${local._s}.Customers|pii_level|Full_PII" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Customers"
      tag_key     = "pii_level"
      tag_value   = "Full_PII"
    }
    "tables|${local._c}.${local._s}.Customers|customer_region|Regional" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Customers"
      tag_key     = "customer_region"
      tag_value   = "Regional"
    }
    "columns|${local._c}.${local._s}.Customers|CustomerRegion|customer_region|EU" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.CustomerRegion"
      tag_key     = "customer_region"
      tag_value   = "EU"
    }
    "columns|${local._c}.${local._s}.Customers|CustomerRegion|data_residency|EU" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.CustomerRegion"
      tag_key     = "data_residency"
      tag_value   = "EU"
    }
    "columns|${local._c}.${local._s}.Customers|SSN|pii_level|Full_PII" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.SSN"
      tag_key     = "pii_level"
      tag_value   = "Full_PII"
    }
    "columns|${local._c}.${local._s}.Customers|SSN|data_residency|US" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.SSN"
      tag_key     = "data_residency"
      tag_value   = "US"
    }
    "columns|${local._c}.${local._s}.Customers|FirstName|pii_level|Limited_PII" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.FirstName"
      tag_key     = "pii_level"
      tag_value   = "Limited_PII"
    }
    "columns|${local._c}.${local._s}.Customers|LastName|pii_level|Limited_PII" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.LastName"
      tag_key     = "pii_level"
      tag_value   = "Limited_PII"
    }
    "columns|${local._c}.${local._s}.Customers|Email|pii_level|Limited_PII" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Customers.Email"
      tag_key     = "pii_level"
      tag_value   = "Limited_PII"
    }

    # ---- SCENARIO 2: PCI (CreditCards) ----
    "tables|${local._c}.${local._s}.CreditCards|pci_clearance|Full" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.CreditCards"
      tag_key     = "pci_clearance"
      tag_value   = "Full"
    }
    "columns|${local._c}.${local._s}.CreditCards|CardNumber|pci_clearance|Full" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.CreditCards.CardNumber"
      tag_key     = "pci_clearance"
      tag_value   = "Full"
    }
    "columns|${local._c}.${local._s}.CreditCards|CVV|pci_clearance|Administrative" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.CreditCards.CVV"
      tag_key     = "pci_clearance"
      tag_value   = "Administrative"
    }

    # ---- SCENARIO 3: AML (Transactions) ----
    "tables|${local._c}.${local._s}.Transactions|aml_clearance|Senior_Investigator" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Transactions"
      tag_key     = "aml_clearance"
      tag_value   = "Senior_Investigator"
    }
    "columns|${local._c}.${local._s}.Transactions|Amount|aml_clearance|Junior_Analyst" = {
      entity_type = "columns"
      entity_name = "${local._c}.${local._s}.Transactions.Amount"
      tag_key     = "aml_clearance"
      tag_value   = "Junior_Analyst"
    }

    # ---- SCENARIOS 4 & 5: Regional (Accounts) ----
    "tables|${local._c}.${local._s}.Accounts|data_residency|Global" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Accounts"
      tag_key     = "data_residency"
      tag_value   = "Global"
    }
    "tables|${local._c}.${local._s}.Accounts|customer_region|Regional" = {
      entity_type = "tables"
      entity_name = "${local._c}.${local._s}.Accounts"
      tag_key     = "customer_region"
      tag_value   = "Regional"
    }
  }
}

resource "databricks_entity_tag_assignment" "finance_abac" {
  for_each = local.finance_tag_assignments

  provider    = databricks.workspace
  entity_type = each.value.entity_type
  entity_name = each.value.entity_name
  tag_key     = each.value.tag_key
  tag_value   = each.value.tag_value

  depends_on = [
    databricks_tag_policy.aml_clearance,
    databricks_tag_policy.pii_level,
    databricks_tag_policy.pci_clearance,
    databricks_tag_policy.customer_region,
    databricks_tag_policy.data_residency,
  ]
}
