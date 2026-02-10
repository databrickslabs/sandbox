# ============================================================================
# Genie: Serverless SQL warehouse (optional override with existing warehouse)
# ============================================================================
# Creates a serverless SQL warehouse for the Genie Space when
# genie_use_existing_warehouse_id is empty. When set, no warehouse is created
# and that ID is used for permissions and for the genie_space.sh create script.
# ============================================================================

locals {
  # Effective warehouse ID: created endpoint, or genie_use_existing_warehouse_id, or genie_default_warehouse_id (deprecated)
  genie_warehouse_id = coalesce(
    join("", databricks_sql_endpoint.genie_warehouse[*].id),
    var.genie_use_existing_warehouse_id,
    var.genie_default_warehouse_id
  )
}

# Create serverless warehouse unless an existing one is explicitly requested via genie_use_existing_warehouse_id.
# (genie_default_warehouse_id does not suppress creation; it is only used as fallback ID when not creating.)
resource "databricks_sql_endpoint" "genie_warehouse" {
  count = var.genie_use_existing_warehouse_id != "" ? 0 : 1

  provider   = databricks.workspace
  name       = var.genie_warehouse_name
  cluster_size = "Small"
  max_num_clusters = 1

  enable_serverless_compute = true
  warehouse_type            = "PRO"

  auto_stop_mins = 15
}
