variable "access_connector_name" {}
variable "resource_group" {}
variable "location" {}
variable "storage_account_name" {}
variable "tags" {}
variable "storage_container_name" {}

variable "access_connector_id" {}
variable "storage_credential_name" {}
variable "external_location_name" {}

variable "catalog_name" {}

# Making force_destroy configurable to prevent accidental data loss
variable "force_destroy_external_location" {
  description = "Whether to force destroy the external location when removing. WARNING: This will delete all data!"
  type        = bool
  default     = false  # Default to false for safety in production
}

# Making catalog force_destroy configurable for production safety
variable "force_destroy_catalog" {
  description = "Whether to force destroy the catalog when removing. WARNING: This will delete all catalog data including schemas and tables!"
  type        = bool
  default     = false  # Default to false for safety in production environments
}