.PHONY: setup generate validate validate-generated plan apply destroy clean help

SHELL := /bin/bash

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
	@if [ ! -f terraform.tfvars ]; then \
		cp terraform.tfvars.example terraform.tfvars; \
		echo "Created terraform.tfvars — edit it with your ABAC config."; \
	else \
		echo "terraform.tfvars already exists — skipping."; \
	fi
	@mkdir -p ddl generated
	@echo "Created ddl/ and generated/ directories."
	@echo ""
	@echo "Next: edit auth.auto.tfvars, then run 'make generate' or 'make plan'."

generate: ## Run generate_abac.py to produce masking SQL + tfvars
	@echo "=== Generate ABAC Config ==="
	python generate_abac.py

validate-generated: ## Validate generated/ files before copying to root
	@echo "=== Validate (generated/) ==="
	@if [ -f generated/masking_functions.sql ]; then \
		python validate_abac.py generated/terraform.tfvars generated/masking_functions.sql; \
	else \
		python validate_abac.py generated/terraform.tfvars; \
	fi

validate: ## Validate root terraform.tfvars (after copying from generated/)
	@echo "=== Validate ==="
	@if [ -f generated/masking_functions.sql ]; then \
		python validate_abac.py terraform.tfvars generated/masking_functions.sql; \
	else \
		python validate_abac.py terraform.tfvars; \
	fi

plan: ## Run terraform init + plan
	@echo "=== Terraform Plan ==="
	terraform init -input=false
	terraform plan

apply: ## Run terraform init + apply (parallelism=1 to avoid tag policy race conditions)
	@echo "=== Terraform Apply ==="
	terraform init -input=false
	terraform apply -parallelism=1

destroy: ## Run terraform destroy
	@echo "=== Terraform Destroy ==="
	terraform destroy

clean: ## Remove generated files, Terraform state, and .terraform/
	@echo "=== Clean ==="
	rm -rf generated/terraform.tfvars generated/masking_functions.sql generated/generated_response.md
	rm -rf .terraform *.tfstate *.tfstate.backup .terraform.lock.hcl
	@echo "Cleaned generated files and Terraform state."
	@echo "NOTE: auth.auto.tfvars and terraform.tfvars were NOT removed."
