# ============================================================================
# Terraform Provider Configuration for Finance ABAC Groups
# ============================================================================

terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.91.0"
    }
  }
  required_version = ">= 1.0"
}

# ----------------------------------------------------------------------------
# Databricks Account-Level Provider
# ----------------------------------------------------------------------------
# This provider is configured for account-level operations (creating groups)

provider "databricks" {
  alias         = "account"
  host          = "https://accounts.cloud.databricks.com"
  account_id    = var.databricks_account_id
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}

# ----------------------------------------------------------------------------
# Databricks Workspace-Level Provider
# ----------------------------------------------------------------------------
# This provider is configured for workspace-level operations (entitlements)
# 
# IMPORTANT: The service principal must be added to the workspace with admin
# permissions to manage entitlements. You can do this via:
# - Account Console → Workspaces → [workspace] → Permissions → Add service principal
# - Or use databricks_mws_permission_assignment with ADMIN permissions

provider "databricks" {
  alias         = "workspace"
  host          = var.databricks_workspace_host
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}
