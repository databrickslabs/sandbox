resource "databricks_catalog" "uc_quickstart" {
  name    = "${var.catalog_name}"
  # storage_root = "${var.storage_root}"
  storage_root = databricks_external_location.uc_external_location.url
  comment = "this catalog is managed by terraform"
  # enable_predictive_optimization = "ENABLE"
  # isolation_mode = "OPEN"
  # properties = {
  #   purpose = "development"
  # }
}