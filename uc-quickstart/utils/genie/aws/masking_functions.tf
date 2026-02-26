# ============================================================================
# Masking Functions Deployment (opt-in)
# ============================================================================
# When sql_warehouse_id is set, executes masking_functions.sql via the
# Databricks Statement Execution API before FGAC policies are created.
# When empty (default), the user must run the SQL manually.
#
# Re-runs automatically when the SQL file content changes (filemd5 trigger).
# CREATE OR REPLACE FUNCTION is idempotent, so re-execution is safe.
# ============================================================================

resource "null_resource" "deploy_masking_functions" {
  count = var.sql_warehouse_id != "" ? 1 : 0

  triggers = {
    sql_hash      = filemd5("masking_functions.sql")
    sql_file      = "${path.module}/masking_functions.sql"
    script        = "${path.module}/deploy_masking_functions.py"
    warehouse_id  = var.sql_warehouse_id
    host          = var.databricks_workspace_host
    client_id     = var.databricks_client_id
    client_secret = var.databricks_client_secret
  }

  provisioner "local-exec" {
    command = "python3 ${self.triggers.script} --sql-file ${self.triggers.sql_file} --warehouse-id ${self.triggers.warehouse_id}"

    environment = {
      DATABRICKS_HOST          = self.triggers.host
      DATABRICKS_CLIENT_ID     = self.triggers.client_id
      DATABRICKS_CLIENT_SECRET = self.triggers.client_secret
    }
  }

  provisioner "local-exec" {
    when    = destroy
    command = "python3 ${self.triggers.script} --sql-file ${self.triggers.sql_file} --warehouse-id ${self.triggers.warehouse_id} --drop"

    environment = {
      DATABRICKS_HOST          = self.triggers.host
      DATABRICKS_CLIENT_ID     = self.triggers.client_id
      DATABRICKS_CLIENT_SECRET = self.triggers.client_secret
    }
  }

  depends_on = [time_sleep.wait_for_tag_propagation]
}
