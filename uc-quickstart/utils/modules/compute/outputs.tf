output "cluster_id" {
  description = "ID of the created cluster"
  value       = databricks_cluster.example.id
}

output "cluster_policy_id" {
  description = "ID of the created cluster policy"
  value       = databricks_cluster_policy.uc_qs_policy.id
}

