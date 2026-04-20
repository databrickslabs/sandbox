# Databricks notebook source
# MAGIC %md
# MAGIC # 👥 Finance ABAC Account Groups Setup
# MAGIC
# MAGIC ## 📋 Overview
# MAGIC This notebook creates all the required **account-level user groups** for finance ABAC scenarios using Databricks Account SCIM API.
# MAGIC
# MAGIC ### 🎯 Groups to Create (5 Total – Minimal Demo)
# MAGIC **Primary:** Use Terraform (genie/aws) to create groups. This script is optional/backup.
# MAGIC 1. **Junior_Analyst** - Masked PII, last-4 card, rounded transaction amounts
# MAGIC 2. **Senior_Analyst** - Unmasked PII, full card, full transaction details
# MAGIC 3. **US_Region_Staff** - Row access limited to US customer data
# MAGIC 4. **EU_Region_Staff** - Row access limited to EU customer data
# MAGIC 5. **Compliance_Officer** - Full unmasked access (all regions, all columns)
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

# Define finance user groups (minimal 5-group demo; Terraform is primary)
finance_groups = {
    "Junior_Analyst": {
        "display_name": "Junior Analyst",
        "description": "Junior analysts with masked PII, last-4 card only, rounded transaction amounts",
        "tags": ["aml_clearance:Junior_Analyst", "pii_level:Limited_PII", "pci_clearance:Basic"]
    },
    "Senior_Analyst": {
        "display_name": "Senior Analyst",
        "description": "Senior analysts with unmasked PII, full card number, full transaction details",
        "tags": ["aml_clearance:Senior_Investigator", "pii_level:Full_PII", "pci_clearance:Full"]
    },
    "US_Region_Staff": {
        "display_name": "US Region Staff",
        "description": "Staff with row access limited to US customer data (GLBA, CCPA)",
        "tags": ["data_residency:US", "customer_region:US"]
    },
    "EU_Region_Staff": {
        "display_name": "EU Region Staff",
        "description": "Staff with row access limited to EU customer data (GDPR)",
        "tags": ["data_residency:EU", "customer_region:EU"]
    },
    "Compliance_Officer": {
        "display_name": "Compliance Officer",
        "description": "Full unmasked access to all regions and columns for audit",
        "tags": ["aml_clearance:Compliance_Officer", "pci_clearance:Administrative"]
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

# Display group mapping to minimal 5 scenarios
print("\n📋 Group to Scenario Mapping (Minimal Demo):\n")

scenario_mapping = {
    "1. PII masking": ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"],
    "2. Fraud/card": ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"],
    "3. Fraud/transactions": ["Junior_Analyst", "Senior_Analyst", "Compliance_Officer"],
    "4. US region": ["US_Region_Staff"],
    "5. EU region": ["EU_Region_Staff"]
}

for scenario, groups in scenario_mapping.items():
    print(f"\n{scenario}")
    print(f"  Groups: {', '.join(groups)}")
    for group in groups:
        if group in finance_groups:
            print(f"    • {group}: {finance_groups[group]['description'][:60]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Next Steps After Account Group Creation
# MAGIC
# MAGIC ### ✅ **Account Groups Created Successfully**
# MAGIC All 5 finance account groups (minimal demo) are now available across all workspaces in your Databricks account:
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
