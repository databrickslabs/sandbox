variable "catalog_name" {
  type        = string
  description = "Name of the catalog to grant permissions on"
}

variable "permissions" {
  type        = map(list(string))
  description = "Map of group to list of permissions (e.g., { group_1 = ['USE_CATALOG'] })"
}

variable "group_1_name" {
  type        = string
  description = "Name of the first group to grant permissions"
}

variable "group_2_name" {
  type        = string
  description = "Name of the second group to grant permissions"
}

variable "group_3_name" {
  type        = string
  description = "Name of the third group to grant permissions"
}
