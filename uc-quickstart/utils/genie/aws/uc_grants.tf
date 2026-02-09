# ============================================================================
# Genie Space: Unity Catalog data access (SELECT, USE_CATALOG, USE_SCHEMA)
# ============================================================================
# Grants base UC privileges to the five finance groups so they can query data
# used by the Genie Space. ABAC policies (defined in SQL) apply at query time
# on top of these base privileges.
# ============================================================================

resource "databricks_grants" "genie_catalog" {
  provider = databricks.workspace
  catalog  = var.uc_catalog_name

  grant {
    principal  = "Junior_Analyst"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
  grant {
    principal  = "Senior_Analyst"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
  grant {
    principal  = "US_Region_Staff"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
  grant {
    principal  = "EU_Region_Staff"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
  grant {
    principal  = "Compliance_Officer"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
}
