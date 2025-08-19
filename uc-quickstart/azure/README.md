### Prerequisites

1. **Microsoft Resource Providers**
- Microsoft.Databricks
- Microsoft.Storage
- Microsoft.ManagedIdentity

2. **Service Principal Permissions**
- Owner - Azure Subscription
- Account Admin - Databricks Account Portal

3. **Existing Resources**
- Azure Databricks workspace
- Resource Group for Access Connectors & Storage Accounts

# Deploy multiple catalogs in Databricks UC

## 1. **Configure TFVAR file**

Create a tfvar file and name it `db.tfvar`

Copy below configurations and replace with relevant entries

```
databricks_resource_id = "https://XX.com"
azure_client_id        = "XX"
azure_client_secret    = "XX"
azure_tenant_id        = "XX"

# Azure RG to deploy assets
resource_group = "XX"

```

Note: Azure and Databricks creds can be injected as environment variables if required. Approach adopted here is for ease of switching environments while testing.

## 2. **Provide expected catalog names as input**

Go to the `main.tf` file. Here you can see 3 entries of env module will be executed.

```
module "sandbox_catalog" {
...
}

module "dev_catalog" {
...
}

module "prod_catalog" {
...    
}

```
By default 3 catalogs (and associated DB and Azure entities) will get deployed:
- sandbox
- dev
- prod

If you need to change the catalog names, navigate to the `variables.tf` in the root directory and update the values given against catalog_1, catalog_2 or catalog_3.

```
variable catalog_1 {
  default = "sandbox"
}

variable catalog_2 {
  default = "dev"
}

variable catalog_3 {
  default = "prod"
}
```

## 3. **Deploy**

Run below commands in sequence to provision the catalogs

```
terraform init
terraform validate
terraform plan -var-file="db.tfvars"
terraform apply -var-file="db.tfvars" -auto-approve
```