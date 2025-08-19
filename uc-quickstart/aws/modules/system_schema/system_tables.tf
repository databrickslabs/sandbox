// Terraform Documentation: https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/system_schema

resource "databricks_system_schema" "access" {
  schema = "access"
}

resource "databricks_system_schema" "compute" {
  schema = "compute"
}

resource "databricks_system_schema" "marketplace" {
  schema = "marketplace"
}

resource "databricks_system_schema" "storage" {
  schema = "storage"
}
