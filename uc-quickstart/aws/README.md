# AWS Unity Catalog Deployment

This directory contains AWS-specific Terraform configurations for deploying Unity Catalog.

## Prerequisites

### Required Permissions
- **Databricks Service Principal:**
  - Workspace Admin
  - Account Admin (for user groups)
  - Metastore Admin (for storage credentials and system schemas)

- **AWS Credentials:**
  - IAM permissions to create S3 buckets, IAM roles, and policies
  - Cross-account access for Unity Catalog integration

### Required Information
- Databricks account ID and workspace ID
- AWS account ID and region
- Service principal client ID and secret

## Configuration

1. **Copy the configuration template:**
   ```bash
   cp template.tfvars.example terraform.tfvars
   ```

2. **Update `terraform.tfvars` with your values:**
   ```hcl
   # Databricks credentials
   databricks_account_id    = "your-account-id"
   databricks_host          = "https://your-workspace.cloud.databricks.com"
   databricks_client_id     = "your-service-principal-id"
   databricks_client_secret = "your-service-principal-secret"
   databricks_workspace_id  = "your-workspace-id"

   # AWS credentials
   aws_access_key    = "your-aws-access-key"
   aws_secret_key    = "your-aws-secret-key"
   aws_account_id    = "your-aws-account-id"
   aws_session_token = "your-session-token"  # Optional for STS
   ```

3. **Customize catalog and group names (optional):**
   
   Edit `variables.tf` to modify default names:
   ```hcl
   variable "catalog_1" { default = "prod" }
   variable "catalog_2" { default = "dev" }
   variable "catalog_3" { default = "sandbox" }
   
   variable "group_1" { default = "production_sp" }
   variable "group_2" { default = "developers" }
   variable "group_3" { default = "sandbox_users" }
   ```

## Deployment

Run the following commands in sequence:

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

## AWS Resources Created

- **S3 Buckets:** One per catalog with versioning and encryption
- **IAM Roles:** Unity Catalog cross-account access roles
- **IAM Policies:** Least-privilege policies for each catalog
- **Databricks Resources:** Catalogs, external locations, storage credentials

## Troubleshooting

**Authentication Issues:**
- Ensure AWS CLI is configured: `aws configure`
- For STS credentials, include `aws_session_token`
- Verify service principal has required Databricks permissions

**Permission Errors:**
- Check IAM user has permissions to create S3 buckets and IAM resources
- Verify service principal is workspace admin in Databricks
- For group creation errors, ensure account admin permissions

**Resource Conflicts:**
- S3 bucket names must be globally unique
- Check for existing IAM roles with same names