variable "catalog_name" {}
# variable "storage_root" {}

variable "external_location_name" {}

variable "databricks_account_id" {}
variable "aws_account_id" {}
variable "storage_prefix" {}
variable "tags" {}
variable "bucket_name" {}

# Making force_destroy configurable to prevent accidental data loss
variable "force_destroy_s3_bucket" {
  description = "Whether to force destroy the S3 bucket when removing. WARNING: This will delete all bucket contents!"
  type        = bool
  default     = false  # Default to false for safety in production
}
