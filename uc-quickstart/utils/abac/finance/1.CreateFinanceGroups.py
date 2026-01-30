# Databricks notebook source
# MAGIC %md
# MAGIC # 👥 Finance ABAC Account Groups Setup
# MAGIC
# MAGIC ## 📋 Overview
# MAGIC This notebook creates all the required **account-level user groups** for finance ABAC scenarios using Databricks Account SCIM API.
# MAGIC
# MAGIC ### 🎯 Groups to Create (15 Total)
# MAGIC 1. **Credit_Card_Support** - Customer service for card inquiries
# MAGIC 2. **Fraud_Analyst** - Fraud detection and investigation
# MAGIC 3. **AML_Investigator_Junior** - Junior AML analysts
# MAGIC 4. **AML_Investigator_Senior** - Senior AML investigators
# MAGIC 5. **Compliance_Officer** - Regulatory compliance oversight
# MAGIC 6. **Equity_Trader** - Equity trading desk
# MAGIC 7. **Fixed_Income_Trader** - Fixed income trading desk
# MAGIC 8. **Research_Analyst** - Research and advisory team
# MAGIC 9. **Risk_Manager** - Risk management and monitoring
# MAGIC 10. **External_Auditor** - External audit firms
# MAGIC 11. **Marketing_Team** - Marketing and analytics
# MAGIC 12. **KYC_Specialist** - Know Your Customer verification
# MAGIC 13. **Regional_EU_Staff** - European region staff
# MAGIC 14. **Regional_US_Staff** - United States region staff
# MAGIC 15. **Regional_APAC_Staff** - Asia-Pacific region staff
# MAGIC
# MAGIC ## ⚠️ Prerequisites
# MAGIC - **Must be run in Databricks workspace** (uses `dbutils` for token)
# MAGIC - **Account admin permissions** to create account-level groups
# MAGIC - Unity Catalog enabled workspace
# MAGIC
# MAGIC ## 🔧 API Notes
# MAGIC - Creates **account-level groups** using Account SCIM API
# MAGIC - Uses `/api/2.0/account/scim/v2/Groups` endpoint
# MAGIC - Groups will be available across all workspaces in the account
# MAGIC
# MAGIC ---

# COMMAND ----------

# Import required libraries
import requests
import json
import os
from typing import List, Dict, Any

# COMMAND ----------

# Configuration - Get from Databricks context
workspace_url = spark.conf.get("spark.databricks.workspaceUrl")
workspace_url = f"https://{workspace_url}"

# Account domain is the workspace domain for account API
account_domain = workspace_url

# Get token from Databricks context (when running in Databricks)
try:
    token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
    print("✅ Token retrieved from Databricks context")
except:
    print("❌ Could not retrieve token from Databricks context")
    print("ℹ️ Make sure this notebook is running in a Databricks workspace")
    raise Exception("Token retrieval failed - ensure notebook is running in Databricks")

# Setup API headers for Account SCIM API
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Use Account SCIM API endpoint for group management
account_scim_url = f"{account_domain}/api/2.0/account/scim/v2/Groups"

print(f"🌐 Account SCIM URL: {account_scim_url}")
print(f"🏦 Account Domain: {account_domain}")
print("⚠️ Note: Creating account-level groups requires account admin permissions")

# COMMAND ----------

# Define all finance user groups with descriptions
finance_groups = {
    "Credit_Card_Support": {
        "display_name": "Credit Card Support",
        "description": "Customer service representatives handling credit card inquiries (PCI-DSS Basic access)",
        "tags": ["pci_clearance:Basic", "payment_role:Customer_Service"]
    },
    "Fraud_Analyst": {
        "display_name": "Fraud Analyst",
        "description": "Fraud detection analysts with full access to payment card data (PCI-DSS Full access)",
        "tags": ["pci_clearance:Full", "payment_role:Fraud_Analyst"]
    },
    "AML_Investigator_Junior": {
        "display_name": "AML Investigator Junior",
        "description": "Junior AML analysts with limited access to transaction data",
        "tags": ["aml_clearance:Junior_Analyst"]
    },
    "AML_Investigator_Senior": {
        "display_name": "AML Investigator Senior",
        "description": "Senior AML investigators with enhanced access to customer and transaction data",
        "tags": ["aml_clearance:Senior_Investigator"]
    },
    "Compliance_Officer": {
        "display_name": "Compliance Officer",
        "description": "Regulatory compliance officers with comprehensive access to all compliance data",
        "tags": ["aml_clearance:Compliance_Officer", "pci_clearance:Administrative", "sox_scope:In_Scope"]
    },
    "Equity_Trader": {
        "display_name": "Equity Trader",
        "description": "Equity trading desk staff with access to equity positions",
        "tags": ["trading_desk:Equity", "information_barrier:Trading_Side"]
    },
    "Fixed_Income_Trader": {
        "display_name": "Fixed Income Trader",
        "description": "Fixed income trading desk staff with access to bond and treasury positions",
        "tags": ["trading_desk:Fixed_Income", "information_barrier:Trading_Side"]
    },
    "Research_Analyst": {
        "display_name": "Research Analyst",
        "description": "Research and advisory team separated by Chinese wall from trading",
        "tags": ["trading_desk:Research", "information_barrier:Advisory_Side"]
    },
    "Risk_Manager": {
        "display_name": "Risk Manager",
        "description": "Risk management team with neutral access across trading desks",
        "tags": ["information_barrier:Neutral", "market_hours:After_Hours"]
    },
    "External_Auditor": {
        "display_name": "External Auditor",
        "description": "External auditors with temporary, time-limited access to financial records",
        "tags": ["audit_project:Q1_SOX_Audit", "sox_scope:In_Scope"]
    },
    "Marketing_Team": {
        "display_name": "Marketing Team",
        "description": "Marketing team with de-identified customer data access",
        "tags": ["pii_level:De_Identified", "data_purpose:Marketing"]
    },
    "KYC_Specialist": {
        "display_name": "KYC Specialist",
        "description": "Know Your Customer specialists with full PII access for verification",
        "tags": ["pii_level:Full_PII", "data_purpose:Verification"]
    },
    "Regional_EU_Staff": {
        "display_name": "Regional EU Staff",
        "description": "Staff based in European Union with access to EU customer data only (GDPR)",
        "tags": ["data_residency:EU", "customer_region:EU"]
    },
    "Regional_US_Staff": {
        "display_name": "Regional US Staff",
        "description": "Staff based in United States with access to US customer data (GLBA, CCPA)",
        "tags": ["data_residency:US", "customer_region:US"]
    },
    "Regional_APAC_Staff": {
        "display_name": "Regional APAC Staff",
        "description": "Staff based in Asia-Pacific region with access to APAC customer data",
        "tags": ["data_residency:APAC", "customer_region:APAC"]
    }
}

print(f"📊 Prepared {len(finance_groups)} finance user groups for creation")
print("\n🏦 Finance Groups:")
for group_name, details in finance_groups.items():
    print(f"  • {group_name}: {details['description'][:60]}...")

# COMMAND ----------

# Utility function to create an account-level group using Account SCIM API
def create_account_group(group_name: str, display_name: str, description: str) -> Dict[str, Any]:
    """
    Create a Databricks account-level group using Account SCIM API
    
    Args:
        group_name: The group name (used as displayName)
        display_name: Human-readable display name (same as group_name)
        description: Group description (for documentation)
    
    Returns:
        API response as dictionary
    """
    
    # Check if group already exists using Account SCIM API
    try:
        list_response = requests.get(account_scim_url, headers=headers)
        if list_response.status_code == 200:
            existing_groups = list_response.json().get('Resources', [])
            for group in existing_groups:
                if group.get('displayName') == group_name:
                    print(f"ℹ️ Account group already exists: {group_name}")
                    print(f"   📋 Group ID: {group.get('id', 'Unknown')}")
                    return {"success": True, "message": "Group already exists", "action": "skipped", "group_id": group.get('id')}
    except Exception as e:
        print(f"⚠️ Could not check existing account groups: {str(e)}")
    
    # Create the group payload using Account SCIM format
    create_payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": group_name
    }
    
    # Make the API call to create account-level group
    try:
        create_response = requests.post(account_scim_url, headers=headers, data=json.dumps(create_payload))
        
        if create_response.status_code == 201:  # SCIM returns 201 for creation
            response_data = create_response.json()
            group_id = response_data.get('id', 'Unknown')
            print(f"✅ Successfully created account group: {group_name}")
            print(f"   📋 Group ID: {group_id}")
            print(f"   📝 Display Name: {display_name}")
            print(f"   📄 Description: {description[:80]}{'...' if len(description) > 80 else ''}")
            return {"success": True, "response": response_data, "action": "created", "group_id": group_id}
        else:
            print(f"❌ Failed to create account group: {group_name}")
            print(f"   Status Code: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            return {"success": False, "error": create_response.text, "action": "failed"}
    
    except Exception as e:
        print(f"❌ Exception creating account group {group_name}: {str(e)}")
        return {"success": False, "error": str(e), "action": "failed"}

# COMMAND ----------

# Create all finance account groups
print("🚀 Starting finance account group creation...\n")

results = {}
success_count = 0
skip_count = 0
failure_count = 0

for group_name, config in finance_groups.items():
    print(f"\n{'='*60}")
    print(f"Creating account group: {group_name}")
    print(f"{'='*60}")
    
    result = create_account_group(
        group_name=group_name,
        display_name=config["display_name"],
        description=config["description"]
    )
    
    results[group_name] = result
    
    if result["success"] and result["action"] == "created":
        success_count += 1
    elif result["success"] and result["action"] == "skipped":
        skip_count += 1
    else:
        failure_count += 1
    
    print()

print(f"\n{'='*60}")
print("📊 ACCOUNT GROUP CREATION SUMMARY")
print(f"{'='*60}")
print(f"✅ Successfully Created: {success_count}")
print(f"⏭️ Already Existed: {skip_count}")
print(f"❌ Failed: {failure_count}")
print(f"📊 Total Groups: {len(finance_groups)}")

# Display created group IDs for reference
print(f"\n📋 Created Group IDs:")
for group_name, result in results.items():
    if result.get("success") and "group_id" in result:
        print(f"  • {group_name}: {result['group_id']}")

# COMMAND ----------

# Verify all account groups were created successfully
print("🔍 Verifying created finance account groups...\n")

try:
    list_response = requests.get(account_scim_url, headers=headers)
    
    if list_response.status_code == 200:
        all_groups = list_response.json().get('Resources', [])
        group_names = [group.get('displayName') for group in all_groups]
        
        print(f"📋 Total account groups: {len(all_groups)}")
        print("\n🏦 Finance account groups found:")
        
        finance_groups_found = []
        for group_name in finance_groups.keys():
            if group_name in group_names:
                finance_groups_found.append(group_name)
                # Find the group ID
                group_id = next((g.get('id') for g in all_groups if g.get('displayName') == group_name), 'Unknown')
                print(f"  ✅ {group_name} (ID: {group_id})")
            else:
                print(f"  ❌ {group_name} - NOT FOUND")
        
        print(f"\n📊 Finance account groups verification:")
        print(f"  • Found: {len(finance_groups_found)}/{len(finance_groups)}")
        
        if len(finance_groups_found) == len(finance_groups):
            print("\n🎉 All finance account groups created and verified successfully!")
            print("\n✅ Next Steps:")
            print("  1. Groups are now available across all workspaces in your account")
            print("  2. Assign users to groups via Databricks Admin Console or API")
            print("  3. Groups can be used in Unity Catalog ABAC policies")
            print("  4. Run 2.CreateFinanceTagPolicies.py to create tag policies")
            print("  5. Run 3.ApplyFinanceSetTags.sql to tag tables")
            print("  6. Run 4.CreateFinanceABACPolicies.sql to create ABAC policies")
        else:
            missing = set(finance_groups.keys()) - set(finance_groups_found)
            print(f"\n⚠️ Missing groups: {missing}")
    
    else:
        print(f"❌ Failed to list account groups. Status: {list_response.status_code}")
        print(f"Response: {list_response.text}")
        
        if list_response.status_code == 403:
            print("\n💡 Troubleshooting:")
            print("  • Ensure you have account admin permissions")
            print("  • Verify the token has account-level permissions")
            print("  • Check if account SCIM API is enabled")

except Exception as e:
    print(f"❌ Exception while listing account groups: {str(e)}")

# COMMAND ----------

# Display group mapping to compliance frameworks
print("\n📋 Group to Compliance Framework Mapping:\n")

compliance_mapping = {
    "🔐 PCI-DSS (Payment Card Security)": ["Credit_Card_Support", "Fraud_Analyst"],
    "💰 AML/KYC (Anti-Money Laundering)": ["AML_Investigator_Junior", "AML_Investigator_Senior", "Compliance_Officer"],
    "🏛️ SEC/MiFID II (Trading Compliance)": ["Equity_Trader", "Fixed_Income_Trader", "Research_Analyst", "Risk_Manager"],
    "🌍 GDPR/CCPA (Data Privacy)": ["Regional_EU_Staff", "Regional_US_Staff", "Regional_APAC_Staff", "Marketing_Team"],
    "📊 SOX (Financial Audit)": ["External_Auditor", "Compliance_Officer"],
    "👤 GLBA (Customer Privacy)": ["KYC_Specialist", "Credit_Card_Support"]
}

for framework, groups in compliance_mapping.items():
    print(f"\n{framework}")
    print(f"  Groups: {', '.join(groups)}")
    for group in groups:
        if group in finance_groups:
            print(f"    • {group}: {finance_groups[group]['description'][:60]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Next Steps After Account Group Creation
# MAGIC
# MAGIC ### ✅ **Account Groups Created Successfully**
# MAGIC All 15 finance account groups are now available across all workspaces in your Databricks account:
# MAGIC
# MAGIC ### 📋 **Ready for ABAC Implementation:**
# MAGIC 1. **Apply Unity Catalog Tag Policies** - Run `2.CreateFinanceTagPolicies.py`
# MAGIC 2. **Tag Tables** - Run `3.ApplyFinanceSetTags.sql`
# MAGIC 3. **Deploy ABAC Policies** - Execute `4.CreateFinanceABACPolicies.sql` ✅ Will now work!
# MAGIC 4. **Assign Users to Groups** - Add users to appropriate account groups
# MAGIC 5. **Test Scenarios** - Validate policies with `5.TestFinanceABACPolicies.sql`
# MAGIC
# MAGIC ### 👥 **User Assignment Options:**
# MAGIC - **Databricks Account Console** - Assign users to account groups via Admin Console
# MAGIC - **Account SCIM API** - Programmatic user assignment to account groups
# MAGIC - **Identity Provider Integration** - Automated user provisioning via SSO
# MAGIC
# MAGIC ### 🔐 **ABAC Policy Binding:**
# MAGIC The ABAC policies in `4.CreateFinanceABACPolicies.sql` will now work with these account groups:
# MAGIC - Policies use `TO 'Group_Name'` syntax to bind to these account groups
# MAGIC - Tag-based conditions will evaluate account group membership
# MAGIC - Row filters and column masks will apply based on account group assignments
# MAGIC
# MAGIC ### 📊 **Account vs Workspace Groups:**
# MAGIC - **Account Groups** (what we created): Available across all workspaces
# MAGIC - **Workspace Groups**: Local to individual workspaces only
# MAGIC - **Unity Catalog ABAC**: Works with both account and workspace groups
# MAGIC
# MAGIC ## 🏦 Finance ABAC Account Groups Ready! 🎉
# MAGIC
# MAGIC Your Databricks account now has all the required groups for comprehensive financial services data governance using Unity Catalog ABAC policies across all workspaces.
# MAGIC
# MAGIC ---
