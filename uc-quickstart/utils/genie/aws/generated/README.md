# Generated Output Folder

`generate_abac.py` writes its output files here:

- `masking_functions.sql` — SQL UDFs for column masking and row filtering
- `terraform.tfvars` — ABAC config (groups, tags, FGAC). Auth comes from `auth.auto.tfvars`.
- `TUNING.md` — Review + tuning checklist before applying
- `generated_response.md` — Full LLM response for reference

**Next steps after generation:**

1. Review `TUNING.md` and tune outputs if needed
2. Run `masking_functions.sql` in your Databricks SQL editor
3. Validate: `python validate_abac.py generated/terraform.tfvars generated/masking_functions.sql`
4. Copy to module root: `cp generated/terraform.tfvars terraform.tfvars`
5. Apply: `terraform init && terraform plan && terraform apply -parallelism=1`

