# Generated Output Folder

`generate_abac.py` writes its output files here:

- `masking_functions.sql` — SQL UDFs for column masking and row filtering
- `abac.auto.tfvars` — ABAC + Genie config (groups, tags, FGAC, Genie Space). Credentials come from `auth.auto.tfvars`.
- `TUNING.md` — Review + tuning checklist before applying
- `generated_response.md` — Full LLM response for reference

**Next steps after generation:**

1. Review `TUNING.md` and tune outputs if needed
2. Validate: `make validate-generated`
3. Apply: `make apply` (validates, promotes to root, runs terraform apply)
