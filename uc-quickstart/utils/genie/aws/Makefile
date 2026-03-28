.PHONY: setup generate validate validate-generated promote plan apply sync-tags destroy clean help

SHELL := /bin/bash
export DATABRICKS_USER_AGENT_EXTRA := genierails/0.1.0

help: ## Show this help
	@grep -E '^[a-z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Copy example files and prompt for credentials
	@echo "=== Setup ==="
	@if [ ! -f auth.auto.tfvars ]; then \
		cp auth.auto.tfvars.example auth.auto.tfvars; \
		echo "Created auth.auto.tfvars — edit it with your credentials."; \
	else \
		echo "auth.auto.tfvars already exists — skipping."; \
	fi
	@if [ ! -f env.auto.tfvars ]; then \
		cp env.auto.tfvars.example env.auto.tfvars; \
		echo "Created env.auto.tfvars — edit it with your tables and environment config."; \
	else \
		echo "env.auto.tfvars already exists — skipping."; \
	fi
	@mkdir -p ddl generated
	@echo "Created ddl/ and generated/ directories."
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit credentials (gitignored):  $$(pwd)/auth.auto.tfvars"
	@echo "  2. Edit tables & environment:       $$(pwd)/env.auto.tfvars"
	@echo "  3. Run:  make generate"

generate: ## Run generate_abac.py to produce masking SQL + tfvars
	@echo "=== Generate ABAC Config ==="
	python generate_abac.py

validate-generated: ## Validate generated/ files before copying to root
	@echo "=== Validate (generated/) ==="
	@if [ -f generated/masking_functions.sql ]; then \
		python validate_abac.py generated/abac.auto.tfvars generated/masking_functions.sql; \
	else \
		python validate_abac.py generated/abac.auto.tfvars; \
	fi

validate: ## Validate root abac.auto.tfvars + masking_functions.sql
	@echo "=== Validate ==="
	@if [ -f masking_functions.sql ]; then \
		python validate_abac.py abac.auto.tfvars masking_functions.sql; \
	elif [ -f generated/masking_functions.sql ]; then \
		python validate_abac.py abac.auto.tfvars generated/masking_functions.sql; \
	else \
		python validate_abac.py abac.auto.tfvars; \
	fi

promote: ## Validate generated/ and copy to root
	@echo "=== Promote generated/ to root ==="
	@if [ -f generated/abac.auto.tfvars ]; then \
		python validate_abac.py generated/abac.auto.tfvars generated/masking_functions.sql && \
		cp generated/abac.auto.tfvars abac.auto.tfvars && \
		cp generated/masking_functions.sql masking_functions.sql && \
		echo "Promoted generated/ files to root."; \
	else \
		echo "No generated/abac.auto.tfvars found. Run 'make generate' first."; \
		exit 1; \
	fi

plan: ## Run terraform init + plan
	@echo "=== Terraform Plan ==="
	terraform init -input=false
	terraform plan

sync-tags: ## Sync tag policy values to Databricks (bypasses provider reordering bug)
	@echo "=== Sync Tag Policies ==="
	@python3 scripts/sync_tag_policies.py

apply: promote sync-tags ## Validate, promote, sync tags, then terraform apply
	@echo "=== Terraform Apply ==="
	terraform init -input=false
	@echo "--- Importing tag policies into state ---"
	@python3 -c "import hcl2,sys; d=hcl2.load(open('abac.auto.tfvars')); [print(tp['key']) for tp in d.get('tag_policies',[])]" 2>/dev/null | \
	  while read key; do \
	    terraform state rm "databricks_tag_policy.policies[\"$$key\"]" 2>/dev/null || true; \
	    terraform import "databricks_tag_policy.policies[\"$$key\"]" "$$key" 2>/dev/null || true; \
	  done
	@echo "--- Running terraform apply ---"
	terraform apply -parallelism=1 -auto-approve

destroy: ## Run terraform destroy (drops masking functions if sql_warehouse_id is set)
	@echo "=== Terraform Destroy ==="
	terraform destroy -auto-approve

clean: ## Remove generated files, Terraform state, and .terraform/
	@echo "=== Clean ==="
	rm -rf generated/abac.auto.tfvars generated/masking_functions.sql generated/generated_response.md
	rm -rf .terraform *.tfstate *.tfstate.backup .terraform.lock.hcl
	@echo "Cleaned generated files and Terraform state."
	@echo "NOTE: auth.auto.tfvars, env.auto.tfvars, and abac.auto.tfvars were NOT removed."
