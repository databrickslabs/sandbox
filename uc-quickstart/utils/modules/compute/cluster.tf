// Terraform Documentation: https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/cluster

// Cluster Version
data "databricks_spark_version" "latest_lts" {
  long_term_support = true
}

data "databricks_node_type" "smallest" {
  local_disk = true
}

// Local variables for cluster configuration
locals {
  autotermination_minutes = 60
}

// Cluster Creation
resource "databricks_cluster" "example" {
  cluster_name            = "UC Quickstart Cluster - ${var.environment}"
  data_security_mode      = "USER_ISOLATION"
  spark_version           = data.databricks_spark_version.latest_lts.id
  node_type_id            = data.databricks_node_type.smallest.id
  autotermination_minutes = local.autotermination_minutes

  autoscale {
    min_workers = 1
    max_workers = 2
  }
}

// Cluster Access Control
resource "databricks_permissions" "cluster_usage" {
  cluster_id = databricks_cluster.example.id

  access_control {
    group_name       = var.group_name
    permission_level = "CAN_MANAGE"
  }
}

