terraform {
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.91.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">=5.76.0"
    }
    time = {
      source = "hashicorp/time"
    }
  }
  required_version = ">=1.0"
}

provider "aws" {
  region = var.region
  # profile = "default"
  # Use env variables for AWS creds if aws cli is not installed
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  # Include the aws_session_token if the temporary credential is used
  token = var.aws_session_token
}

// initialize provider at account level for provisioning workspace with AWS PrivateLink
provider "databricks" {
  alias         = "workspace"
  # profile = "db-aws"
  host  = var.databricks_host
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}

provider "databricks" {
  alias         = "account"
  host          = "https://accounts.cloud.databricks.com"
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
  account_id    = var.databricks_account_id
}