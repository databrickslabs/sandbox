variable "access_connector_name" {
  type        = string
  description = "Name of the Azure access connector for Unity Catalog"
}

variable "resource_group" {
  type        = string
  description = "Azure resource group name"
}

variable "location" {
  type        = string
  description = "Azure region/location for resources"
}

variable "storage_account_name" {
  type        = string
  description = "Name of the Azure storage account"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to Azure resources"
}

variable "storage_container_name" {
  type        = string
  description = "Name of the storage container"
}

variable "access_connector_id" {
  type        = string
  description = "ID of the Azure access connector"
}

variable "storage_credential_name" {
  type        = string
  description = "Name of the storage credential in Unity Catalog"
}

variable "external_location_name" {
  type        = string
  description = "Name of the external location in Unity Catalog"
}

variable "catalog_name" {
  type        = string
  description = "Name of the Unity Catalog catalog to create"
}

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