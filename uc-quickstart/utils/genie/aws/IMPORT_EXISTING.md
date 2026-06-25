# Import Existing Resources (Overwrite / Adopt)

If the warehouse, groups, or tag policies **already exist**, Terraform will fail with "already exists". Use the import script below so Terraform can adopt and overwrite them.

## Prerequisites

Before running the import script, ensure:

1. `auth.auto.tfvars` is configured with valid credentials and `env.auto.tfvars` with your environment.
2. `abac.auto.tfvars` is configured with the groups and tag policies you want to import.
3. `terraform init` has been run.

## Usage

From **genie/aws**:

```bash
# Import all existing resources (groups, tag policies, FGAC policies)
./scripts/import_existing.sh

# Import only groups
./scripts/import_existing.sh --groups-only

# Import only tag policies
./scripts/import_existing.sh --tags-only

# Dry run — show what would be imported without running terraform import
./scripts/import_existing.sh --dry-run
```

The script reads group names from `abac.auto.tfvars` and tag policy keys from the same file. For each resource, it checks whether an import is needed and runs `terraform import` if the resource exists in Databricks but not in Terraform state.

## Optional: reuse an existing warehouse

To use an existing warehouse instead of auto-creating one, set in **env.auto.tfvars**:

```hcl
sql_warehouse_id = "<WAREHOUSE_ID>"
```

Terraform will skip warehouse creation and reuse this ID for masking function deployment, Genie Space, and outputs.
