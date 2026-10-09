# Copy to config.sh and fill in. Every script sources it.

# AWS account that holds the HealthLake data stores
export AWS_PROFILE="your-aws-profile"
export AWS_REGION="us-east-1"
# Optional: comma-separated data store names to serve; empty serves every ACTIVE data store
export HEALTHLAKE_DATASTORES=""
# Optional: comma-separated roles created by terraform/ in other AWS accounts that hold data stores
export ADDITIONAL_AWS_ROLE_ARNS=""

# Workspace that hosts the app (Databricks CLI profile)
export DATABRICKS_CONFIG_PROFILE="your-hosting-profile"
export APP_NAME="healthlake-opensharing"
export RECIPIENT_SP_NAME="healthlake-opensharing-recipient"
# share: one Unity Catalog catalog per data store; schema: one catalog, a schema per data store
export LAYOUT="share"

# Workspace that mounts the shares; can be another workspace and metastore
export CONSUMER_PROFILE="$DATABRICKS_CONFIG_PROFILE"
export PROVIDER_NAME="healthlake_opensharing"
# catalogs are named <CATALOG_PREFIX><share>
export CATALOG_PREFIX="healthlake_"

# Terraform (AWS side)
export TF_VAR_name_prefix="healthlake-opensharing"
export TF_VAR_tags='{"Service":"healthlake-opensharing"}'
# Set if this account already has an IAM OIDC provider for the hosting workspace
export TF_VAR_oidc_provider_arn=""
