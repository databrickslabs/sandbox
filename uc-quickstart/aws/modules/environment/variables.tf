variable "catalog_name" {
  type        = string
  description = "Name of the Unity Catalog catalog to create"
}

# variable "storage_root" {}

variable "external_location_name" {
  type        = string
  description = "Name of the external location to create"
}

variable "databricks_account_id" {
  type        = string
  description = "The Databricks account ID"
}

variable "aws_account_id" {
  type        = string
  description = "The AWS account ID where resources will be created"
}

variable "storage_prefix" {
  type        = string
  description = "Prefix for storage locations"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to resources"
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket for storage"
}

# Making force_destroy configurable to prevent accidental data loss
variable "force_destroy_s3_bucket" {
  description = "Whether to force destroy the S3 bucket when removing. WARNING: This will delete all bucket contents!"
  type        = bool
  default     = false  # Default to false for safety in production
}
