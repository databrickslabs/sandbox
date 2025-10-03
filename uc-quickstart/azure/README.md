# Azure Unity Catalog Deployment

This directory contains Azure-specific Terraform configurations for deploying Unity Catalog.

## Prerequisites

### Required Permissions
- **Azure Service Principal:**
  - Owner role on Azure Subscription
  - Contributor role on Resource Group

- **Databricks Service Principal:**
  - Account Admin (for user groups)
  - Workspace Admin 
  - Metastore Admin (for storage credentials and system schemas)

### Existing Resources Required
- Azure Databricks Workspace
- Resource Group for deploying storage accounts and access connectors

## Authentication

### Azure CLI (Recommended)
```bash
# Install Azure CLI
brew install azure-cli

# Login and set subscription
az login
az account set --subscription "your-subscription-id"
```

### Service Principal (Alternative)
Set environment variables:
```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_TENANT_ID="your-tenant-id"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
```

## Configuration

1. **Copy the configuration template:**
   ```bash
   cp template.tfvars.example terraform.tfvars
   ```

2. **Update `terraform.tfvars` with your values:**
   ```hcl
   # Databricks credentials
   databricks_account_id   = "your-account-id"
   databricks_host         = "https://adb-workspace-id.region.azuredatabricks.net"
   databricks_workspace_id = "your-workspace-id"

   # Azure-Managed Service Principal credentials
   databricks_resource_id  = "/subscriptions/.../Microsoft.Databricks/workspaces/..."
   azure_client_id         = "your-service-principal-app-id"
   azure_client_secret     = "your-service-principal-secret"
   azure_tenant_id         = "your-tenant-id"

   # Azure resources
   resource_group = "your-resource-group"
   location       = "Australia East"
   ```

3. **Customize catalog and group names (optional):**
   
   Edit `variables.tf` to modify default names:
   ```hcl
   variable "catalog_1" { default = "sandbox" }
   variable "catalog_2" { default = "dev" }
   variable "catalog_3" { default = "prod" }
   ```

## Finding Azure Credentials

| Credential | Location |
|------------|----------|
| `databricks_resource_id` | Azure Portal → Databricks workspace → Properties → Resource ID |
| `azure_client_id` | Azure Portal → Azure AD → App registrations → Your app → Application ID |
| `azure_client_secret` | Azure Portal → Azure AD → App registrations → Your app → Certificates & secrets |
| `azure_tenant_id` | Azure Portal → Azure AD → Overview → Tenant ID |

## Deployment

Run the following commands in sequence:

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

## Azure Resources Created

- **Storage Accounts:** One per catalog with containers and RBAC
- **Access Connectors:** Managed identities for Databricks access
- **Role Assignments:** Least-privilege RBAC for each catalog
- **Databricks Resources:** Catalogs, external locations, storage credentials

## Troubleshooting

**Authentication Issues:**
- Ensure Azure CLI is logged in: `az account show`
- Verify service principal has required permissions
- Check subscription ID is correct

**Permission Errors:**
- Service principal needs Owner/Contributor on subscription/resource group
- Databricks service principal needs Account Admin for groups
- For storage credential errors, check metastore admin permissions

**Resource Conflicts:**
- Storage account names must be globally unique (3-24 lowercase chars)
- Check for existing access connectors with same names
- Verify resource group exists and you have permissions