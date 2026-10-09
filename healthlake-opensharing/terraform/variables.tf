variable "aws_region" {
  type = string
}

variable "name_prefix" {
  type        = string
  default     = "healthlake-opensharing"
  description = "IAM role is named <name_prefix>-reader"
}

variable "oidc_issuer" {
  type        = string
  description = "Workspace OIDC issuer, e.g. https://<workspace-host>/oidc"
}

variable "oidc_audience" {
  type        = string
  description = "aud claim of the app service principal's Databricks token (the workspace ID)"
}

variable "oidc_provider_arn" {
  type        = string
  default     = ""
  description = "Existing IAM OIDC provider for oidc_issuer; empty creates one"
}

variable "app_sp_client_id" {
  type        = string
  description = "sub claim of the app service principal's Databricks token"
}

variable "healthlake_stores" {
  type = list(object({
    link_db         = string
    service_account = string
    target_db       = string
  }))
  description = "Glue resource link, owning HealthLake service account, and target database of each data store"
}

variable "tags" {
  type    = map(string)
  default = {}
}
