# ============================================================================
# SQL Warehouse (shared by masking function deployment + Genie Space)
# ============================================================================
# When sql_warehouse_id is set in auth.auto.tfvars, that existing warehouse is
# reused for everything. When empty, Terraform auto-creates a serverless
# warehouse. The effective ID is exposed as local.effective_warehouse_id.
# ============================================================================

locals {
  effective_warehouse_id = (
    var.sql_warehouse_id != ""
    ? var.sql_warehouse_id
    : databricks_sql_endpoint.warehouse[0].id
  )
}

resource "databricks_sql_endpoint" "warehouse" {
  count = var.sql_warehouse_id != "" ? 0 : 1

  provider         = databricks.workspace
  name             = var.warehouse_name
  cluster_size     = "Small"
  max_num_clusters = 1

  enable_serverless_compute = true
  warehouse_type            = "PRO"

  auto_stop_mins = 15
}
