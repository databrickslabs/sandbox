# Import Existing Resources (Overwrite / Adopt)

If the warehouse, groups, or tag policies **already exist**, Terraform will fail with "already exists". Use the **one script** below so Terraform can adopt and overwrite them.

## One-time setup

1. Copy the example file and add your IDs:
   ```bash
   cp import_ids.env.example import_ids.env
   ```
2. Fill in **import_ids.env**:
   - **WAREHOUSE_ID** – From workspace: **SQL → Warehouses** → open "Genie Finance Warehouse" → ID from URL or details.
   - **GROUP_ID_Junior_Analyst**, **GROUP_ID_Senior_Analyst**, **GROUP_ID_US_Region_Staff**, **GROUP_ID_EU_Region_Staff**, **GROUP_ID_Compliance_Officer** – From **Account Console → Identity and access → Groups** → open each group → copy ID.

Leave a line commented (with `#`) if you don’t have that ID; that resource will be skipped.

## Run the import script

From **genie/aws**:

```bash
./scripts/import_existing.sh
```

The script imports the warehouse (if `WAREHOUSE_ID` is set), the five groups (if each `GROUP_ID_*` is set), and all five tag policies. After that, **terraform apply** will manage and overwrite config to match the .tf files.

## Optional: warehouse only (no Terraform management)

To use an existing warehouse **without** importing it, set in **terraform.tfvars**:

```hcl
genie_use_existing_warehouse_id = "<WAREHOUSE_ID>"
```

Then Terraform won’t create a warehouse and will use this ID for genie_space.sh create and outputs.
