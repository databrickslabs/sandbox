# Deploy multiple catalogs in Databricks UC

## 1. **Configure TFVAR file**

Copy the file `template.tfvars.example` and name it `db.tffvar`

Minimum Permissions for bootstrap SP :

a) Workspace Admin
b) Create Catalog Permisions

Update the configuration with the relavant entries:

```
#Databricks credentials
databricks_account_id    = "XXX" // Databricks account ID.
databricks_host          = "https://xxx.cloud.databricks.com" // The URL of the workspace used for UC deployment
databricks_token(Optional)         = "XXX" // The personal access token of the service pricipal used to provision the resources in the Databricks workspace ### 
databricks_client_id     = "XXX" // Service principal ID for Databricks with admin permissions.
databricks_client_secret = "XXX" // Secret for the corresponding service principal.
databricks_workspace_id  = "XX" // The ID of the workspace to enable Unity Catalog


# AWS credentials
aws_access_key    = "XXX" // Specifies an AWS access key associated with an IAM user or role
aws_secret_key    = "XXX" // Specifies the secret key associated with the access key. This is essentially the "password" for the access key.
aws_account_id    = "XXX" // AWS account ID where resources will be deployed.
aws_session_token = "XXXX" // - Optional Specifies the session token value that is required if you are using temporary security credentials that you retrieved directly from AWS Security Token Service operations.

```

Note: AWS and Databricks creds can be injected as environment variables if required. Approach adopted here is for ease of switching environments while testing.

## 2. **Provide expected catalog names as input**

Go to the `main.tf` file. Here you can see the entries of the different modules moduleswill be executed.

By default 3 catalogs (and associated DB and AWS entities) will get deployed:
- dev
- prod
- sandbox
and 3 groups will be created: 
- production_sp This is the group of the service pricipals used to write in the prod catalog
- developers
- sandbox users 
If you need to change the catalog or users names, navigate to the `variables.tf` in the root directory and update the values given against catalog_1, catalog_2 or catalog_3, group_1, group_2 and group_3, and the associated permission.


```

variable "catalog_1" {
  default = "prod"
}

variable "catalog_2" {
  default = "dev"
}

variable "catalog_3" {
  default = "sandbox"
}

variable "group_1" {
  default = "production_sp"
}

variable "group_2" {
  default = "developers"
}

variable "group_3" {
  default = "sandbox_users"
}



variable "catalog_1_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["USE_CATALOG", "SELECT"]
    group_3 = []
  }
}

variable "catalog_2_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["ALL_PRIVILEGES"]
    group_3 = []
  }
}

variable "catalog_3_permissions" {
  type = map(list(string))
  default = {
    group_1 = ["ALL_PRIVILEGES"]
    group_2 = ["ALL_PRIVILEGES"]
    group_3 = ["ALL_PRIVILEGES"]
  }
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
