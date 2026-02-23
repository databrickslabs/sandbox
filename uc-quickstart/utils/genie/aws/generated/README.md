# Generated Output Folder

`generate_abac.py` writes its output files here:

- `masking_functions.sql` — SQL UDFs for column masking and row filtering
- `terraform.tfvars` — Groups, tag policies, tag assignments, and FGAC policies
- `generated_response.md` — Full LLM response for reference

**Next steps after generation:**

1. Review the generated files
2. Run `masking_functions.sql` in your Databricks SQL editor
3. Copy `terraform.tfvars` to the module root and fill in authentication fields
4. `terraform init && terraform plan && terraform apply`
