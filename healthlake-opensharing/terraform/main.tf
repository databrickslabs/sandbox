# AWS side of healthlake-opensharing, applied once per AWS account that holds
# HealthLake data stores: an IAM role only the app's service principal can
# assume, and Lake Formation grants on each data store it serves.
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.100"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = var.tags
  }
}

locals {
  issuer_host       = trimprefix(var.oidc_issuer, "https://")
  oidc_provider_arn = var.oidc_provider_arn != "" ? var.oidc_provider_arn : aws_iam_openid_connect_provider.workspace[0].arn
  stores            = { for s in var.healthlake_stores : s.link_db => s }
}

# An account can hold only one provider per issuer URL; pass oidc_provider_arn
# to reuse one that already trusts this workspace.
resource "aws_iam_openid_connect_provider" "workspace" {
  count          = var.oidc_provider_arn == "" ? 1 : 0
  url            = var.oidc_issuer
  client_id_list = [var.oidc_audience]
}

resource "aws_iam_role" "app" {
  name = "${var.name_prefix}-reader"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.issuer_host}:sub" = var.app_sp_client_id
          "${local.issuer_host}:aud" = var.oidc_audience
        }
      }
    }]
  })
}

# No S3 permissions: every byte is read with credentials Lake Formation vends per table.
resource "aws_iam_role_policy" "app" {
  name = "glue-read-lf-vending"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["lakeformation:GetDataAccess", "lakeformation:GetTemporaryGlueTableCredentials"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["healthlake:ListFHIRDatastores"]
        Resource = "*"
      }
    ]
  })
}

# Lake Formation rejects grants to principals IAM hasn't propagated yet
resource "time_sleep" "iam_propagation" {
  depends_on      = [aws_iam_role.app]
  create_duration = "60s"
}

resource "aws_lakeformation_permissions" "link_describe" {
  for_each    = local.stores
  principal   = aws_iam_role.app.arn
  permissions = ["DESCRIBE"]

  database {
    name = each.value.link_db
  }

  depends_on = [time_sleep.iam_propagation]
}

resource "aws_lakeformation_permissions" "target_select" {
  for_each    = local.stores
  principal   = aws_iam_role.app.arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    catalog_id    = each.value.service_account
    database_name = each.value.target_db
    wildcard      = true
  }

  depends_on = [time_sleep.iam_propagation]
}

output "role_arn" {
  value = aws_iam_role.app.arn
}
