# ============================================================================
# Genie Space — dual-mode lifecycle
# ============================================================================
# Mode 1 (existing):  genie_space_id is set → set ACLs on the existing space.
# Mode 2 (greenfield): genie_space_id is empty → create a new space from
#                       uc_tables, set ACLs, and trash on destroy.
# ============================================================================

# --------------------------------------------------------------------------
# Mode 1: ACLs on an existing Genie Space
# --------------------------------------------------------------------------

resource "null_resource" "genie_space_acls" {
  count = var.genie_space_id != "" ? 1 : 0

  triggers = {
    space_id = var.genie_space_id
    groups   = join(",", keys(var.groups))
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/genie_space.sh set-acls"

    environment = {
      DATABRICKS_HOST          = var.databricks_workspace_host
      DATABRICKS_CLIENT_ID     = var.databricks_client_id
      DATABRICKS_CLIENT_SECRET = var.databricks_client_secret
      GENIE_SPACE_OBJECT_ID    = var.genie_space_id
      GENIE_GROUPS_CSV         = join(",", keys(var.groups))
    }
  }

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
  ]
}

# --------------------------------------------------------------------------
# Mode 2: Create a new Genie Space + set ACLs, trash on destroy
# --------------------------------------------------------------------------

resource "null_resource" "genie_space_create" {
  count = var.genie_space_id == "" && length(var.uc_tables) > 0 ? 1 : 0

  triggers = {
    tables        = join(",", var.uc_tables)
    groups        = join(",", keys(var.groups))
    warehouse_id  = local.effective_warehouse_id
    id_file       = "${path.module}/.genie_space_id"
    script        = "${path.module}/scripts/genie_space.sh"
    host          = var.databricks_workspace_host
    client_id     = var.databricks_client_id
    client_secret = var.databricks_client_secret
  }

  provisioner "local-exec" {
    command = "${self.triggers.script} create"

    environment = {
      DATABRICKS_HOST          = self.triggers.host
      DATABRICKS_CLIENT_ID     = self.triggers.client_id
      DATABRICKS_CLIENT_SECRET = self.triggers.client_secret
      GENIE_TABLES_CSV         = self.triggers.tables
      GENIE_GROUPS_CSV         = self.triggers.groups
      GENIE_WAREHOUSE_ID       = self.triggers.warehouse_id
      GENIE_TITLE              = var.genie_space_title
      GENIE_DESCRIPTION        = var.genie_space_description
      GENIE_SAMPLE_QUESTIONS   = length(var.genie_sample_questions) > 0 ? jsonencode(var.genie_sample_questions) : ""
      GENIE_INSTRUCTIONS       = var.genie_instructions
      GENIE_BENCHMARKS         = length(var.genie_benchmarks) > 0 ? jsonencode(var.genie_benchmarks) : ""
      GENIE_SQL_FILTERS        = length(var.genie_sql_filters) > 0 ? jsonencode(var.genie_sql_filters) : ""
      GENIE_SQL_EXPRESSIONS    = length(var.genie_sql_expressions) > 0 ? jsonencode(var.genie_sql_expressions) : ""
      GENIE_SQL_MEASURES       = length(var.genie_sql_measures) > 0 ? jsonencode(var.genie_sql_measures) : ""
      GENIE_JOIN_SPECS         = length(var.genie_join_specs) > 0 ? jsonencode(var.genie_join_specs) : ""
      GENIE_ID_FILE            = self.triggers.id_file
    }
  }

  provisioner "local-exec" {
    when    = destroy
    command = "${self.triggers.script} trash"

    environment = {
      DATABRICKS_HOST          = self.triggers.host
      DATABRICKS_CLIENT_ID     = self.triggers.client_id
      DATABRICKS_CLIENT_SECRET = self.triggers.client_secret
      GENIE_ID_FILE            = self.triggers.id_file
    }
  }

  depends_on = [
    databricks_group.groups,
    databricks_mws_permission_assignment.group_assignments,
    databricks_sql_endpoint.warehouse,
    null_resource.deploy_masking_functions,
  ]
}
