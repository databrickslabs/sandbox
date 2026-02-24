# Import Existing Resources (Overwrite / Adopt)

If the warehouse, groups, or tag policies **already exist**, Terraform will fail with "already exists". Use the import script below so Terraform can adopt and overwrite them.

## Prerequisites

Before running the import script, ensure:

1. `auth.auto.tfvars` is configured with valid credentials.
2. `terraform.tfvars` is configured with the groups and tag policies you want to import.
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

The script reads group names from `terraform.tfvars` and tag policy keys from the same file. For each resource, it checks whether an import is needed and runs `terraform import` if the resource exists in Databricks but not in Terraform state.

## Optional: warehouse only (no Terraform management)

To use an existing warehouse **without** importing it, set in **terraform.tfvars**:

```hcl
genie_use_existing_warehouse_id = "<WAREHOUSE_ID>"
```

Then Terraform won't create a warehouse and will use this ID for genie_space.sh create and outputs.
