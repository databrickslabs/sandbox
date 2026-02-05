# Finance ABAC Account Groups - Terraform Module

This Terraform module creates **account-level user groups** for finance ABAC (Attribute-Based Access Control) scenarios in Databricks Unity Catalog, assigns them to a workspace, and grants **consumer access entitlements**.

## 📋 Overview

Creates 15 account-level groups aligned with financial services compliance frameworks:

| Group | Description | Compliance |
|-------|-------------|------------|
| `Credit_Card_Support` | Customer service for card inquiries | PCI-DSS |
| `Fraud_Analyst` | Fraud detection and investigation | PCI-DSS |
| `AML_Investigator_Junior` | Junior AML analysts | AML/KYC |
| `AML_Investigator_Senior` | Senior AML investigators | AML/KYC |
| `Compliance_Officer` | Regulatory compliance oversight | AML/SOX |
| `Equity_Trader` | Equity trading desk | SEC/MiFID II |
| `Fixed_Income_Trader` | Fixed income trading desk | SEC/MiFID II |
| `Research_Analyst` | Research and advisory team | SEC/MiFID II |
| `Risk_Manager` | Risk management and monitoring | SEC/MiFID II |
| `External_Auditor` | External audit firms | SOX |
| `Marketing_Team` | Marketing and analytics | GDPR/CCPA |
| `KYC_Specialist` | Know Your Customer verification | GLBA |
| `Regional_EU_Staff` | European region staff | GDPR |
| `Regional_US_Staff` | United States region staff | CCPA/GLBA |
| `Regional_APAC_Staff` | Asia-Pacific region staff | Local Privacy |

## 🚀 Usage

### 1. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your Databricks credentials:

```hcl
# Account configuration
databricks_account_id    = "your-account-id"
databricks_client_id     = "your-service-principal-client-id"
databricks_client_secret = "your-service-principal-secret"

# Workspace configuration
databricks_workspace_id   = "1234567890123456"
databricks_workspace_host = "https://your-workspace.cloud.databricks.com"
```

### 2. Initialize and Apply

```bash
terraform init
terraform plan
terraform apply
```

### 3. Verify Groups

After applying, you can verify the groups in the Databricks Account Console under **User Management > Groups**.

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `finance_group_ids` | Map of group names to their Databricks group IDs |
| `finance_group_names` | List of all created finance group names |
| `compliance_framework_groups` | Groups organized by compliance framework |
| `workspace_assignments` | Map of group names to workspace assignment IDs |
| `group_entitlements` | Summary of entitlements granted to each group |

## 🎫 Consumer Entitlements (Minimal Permissions)

This module grants **minimal consumer entitlement** following the principle of least privilege, using the [`databricks_entitlements`](https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/entitlements) resource:

| Entitlement | Value | Description |
|-------------|-------|-------------|
| `workspace_consume` | ✅ `true` | Minimal consumer access (can access but not create resources) |

Groups are assigned to the workspace with minimal consumer access only.

## 🔐 Authentication

This module requires a Databricks service principal with **Account Admin** permissions.

### Required Permissions
- Create account-level groups
- Manage group membership (if assigning users)
- Assign groups to workspaces (if using workspace assignment)

### Environment Variables (Alternative)

```bash
export DATABRICKS_ACCOUNT_ID="your-account-id"
export DATABRICKS_CLIENT_ID="your-client-id"
export DATABRICKS_CLIENT_SECRET="your-client-secret"
```

## 🏗️ Architecture

```
Account Level                              Workspace Level
┌─────────────────────────────┐           ┌─────────────────────────────┐
│  Account Groups (15)        │           │  Entitlements (Minimal)     │
│  ├── Credit_Card_Support    │──────────▶│                             │
│  ├── Fraud_Analyst          │  assign   │  workspace_consume ✅       │
│  ├── AML_Investigator_*     │──────────▶│                             │
│  ├── Compliance_Officer     │           │                             │
│  ├── *_Trader               │           └─────────────────────────────┘
│  ├── Research_Analyst       │
│  ├── Risk_Manager           │           Principle of Least Privilege
│  ├── External_Auditor       │           Minimal consumer access only
│  ├── Marketing_Team         │
│  ├── KYC_Specialist         │
│  └── Regional_*_Staff       │
└─────────────────────────────┘
```

## 🎯 Next Steps

After creating the groups:

1. **Assign Users** - Add users to appropriate groups via Account Console or SCIM API
2. **Create Tag Policies** - Define Unity Catalog tag policies for ABAC
3. **Tag Tables** - Apply tags to tables and columns
4. **Create ABAC Policies** - Implement row filters and column masks using group membership

## 📊 Compliance Framework Mapping

### PCI-DSS (Payment Card Security)
- `Credit_Card_Support` - Basic PCI access
- `Fraud_Analyst` - Full PCI access

### AML/KYC (Anti-Money Laundering)
- `AML_Investigator_Junior` - Limited transaction access
- `AML_Investigator_Senior` - Enhanced access
- `Compliance_Officer` - Full compliance access

### SEC/MiFID II (Trading Compliance)
- `Equity_Trader` - Trading side
- `Fixed_Income_Trader` - Trading side
- `Research_Analyst` - Advisory side (Chinese wall)
- `Risk_Manager` - Neutral access

### GDPR/CCPA (Data Privacy)
- `Regional_EU_Staff` - EU data only
- `Regional_US_Staff` - US data only
- `Regional_APAC_Staff` - APAC data only
- `Marketing_Team` - De-identified data only

### SOX (Financial Audit)
- `External_Auditor` - Temporary audit access
- `Compliance_Officer` - Audit oversight

### GLBA (Customer Privacy)
- `KYC_Specialist` - Full PII for verification
- `Credit_Card_Support` - Limited customer data
