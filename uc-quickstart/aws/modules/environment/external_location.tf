resource "null_resource" "previous" {}

# Wait to prevent race condition between IAM role and external location validation
resource "time_sleep" "wait_60_seconds" {
  depends_on      = [null_resource.previous]
  create_duration = "60s"
}

locals {
  uc_iam_role        = "${var.catalog_name}-catalog"
  uc_catalog_name_us = replace(var.catalog_name, "-", "_")
}

# Storage Credential (created before role): https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/unity-catalog#configure-external-locations-and-credentials
resource "databricks_storage_credential" "uc_storage_cred" {
  name = "${var.external_location_name}-storage-credential"
  aws_iam_role {
    role_arn = "arn:aws:iam::${var.aws_account_id}:role/${local.uc_iam_role}"
  }
}

# Unity Catalog Trust Policy - Data Source
data "databricks_aws_unity_catalog_assume_role_policy" "unity_catalog" {
  aws_account_id = var.aws_account_id
  aws_partition  = "aws"
  role_name      = local.uc_iam_role
  unity_catalog_iam_arn = "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL"
  external_id    = databricks_storage_credential.uc_storage_cred.aws_iam_role[0].external_id
}

# Unity Catalog Policy - Data Source
data "databricks_aws_unity_catalog_policy" "unity_catalog" {
  aws_account_id = var.aws_account_id
  aws_partition  = "aws"
  bucket_name    = var.bucket_name
  role_name      = local.uc_iam_role
}

# Unity Catalog Policy
resource "aws_iam_policy" "unity_catalog" {
  name   = "${var.catalog_name}-catalog-policy"
  policy = data.databricks_aws_unity_catalog_policy.unity_catalog.json
}

# Unity Catalog Role
resource "aws_iam_role" "unity_catalog" {
  name               = local.uc_iam_role
  assume_role_policy = data.databricks_aws_unity_catalog_assume_role_policy.unity_catalog.json
}

# Unity Catalog Policy Attachment
resource "aws_iam_policy_attachment" "unity_catalog_attach" {
  name       = "${var.catalog_name}-unity_catalog_policy_attach"
  roles      = [aws_iam_role.unity_catalog.name]
  policy_arn = aws_iam_policy.unity_catalog.arn
}

# Unity Catalog S3
resource "aws_s3_bucket" "unity_catalog_bucket" {
  bucket        = var.bucket_name
  # Made configurable to prevent accidental data loss in production
  # This controls whether all bucket contents are deleted on terraform destroy
  force_destroy = var.force_destroy_s3_bucket
}

resource "aws_s3_bucket_versioning" "unity_catalog_versioning" {
  bucket = aws_s3_bucket.unity_catalog_bucket.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_public_access_block" "unity_catalog" {
  bucket                  = aws_s3_bucket.unity_catalog_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  depends_on              = [aws_s3_bucket.unity_catalog_bucket]
}


# External Location
resource "databricks_external_location" "uc_external_location" {
  name            = "${var.external_location_name}"
  url             = "s3://${aws_s3_bucket.unity_catalog_bucket.id}"
  credential_name = databricks_storage_credential.uc_storage_cred.id
  depends_on      = [aws_iam_policy_attachment.unity_catalog_attach, time_sleep.wait_60_seconds]
}