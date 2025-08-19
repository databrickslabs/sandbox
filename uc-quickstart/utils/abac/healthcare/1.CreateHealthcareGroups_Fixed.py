# Databricks notebook source
# MAGIC %md
# MAGIC # 👥 Healthcare ABAC Account Groups Setup
# MAGIC
# MAGIC ## 📋 Overview
# MAGIC This notebook creates all the required **account-level user groups** for the 7 healthcare ABAC scenarios using Databricks Account SCIM API.
# MAGIC
# MAGIC ### 🎯 Groups to Create
# MAGIC Based on the ABAC policies and scenarios, we need the following account groups:
# MAGIC
# MAGIC 1. **Healthcare_Analyst** - Population health analytics
# MAGIC 2. **Lab_Technician** - Laboratory operations  
# MAGIC 3. **External_Auditor** - Temporary audit access
# MAGIC 4. **Healthcare_Worker** - General healthcare staff
# MAGIC 5. **Regional_Staff** - Location-specific access
# MAGIC 6. **Population_Health_Researcher** - Research studies
# MAGIC 7. **Billing_Clerk** - Basic billing operations
# MAGIC 8. **Insurance_Coordinator** - Insurance processing
# MAGIC 9. **Financial_Manager** - Full financial access
# MAGIC 10. **Junior_Staff** - Entry-level healthcare workers
# MAGIC 11. **Senior_Staff** - Experienced healthcare workers
# MAGIC 12. **Department_Head** - Leadership roles
# MAGIC
# MAGIC ## ⚠️ Prerequisites
# MAGIC - **Must be run in Databricks workspace** (uses `dbutils` for token)
# MAGIC - **Account admin permissions** to create account-level groups
# MAGIC - Unity Catalog enabled workspace
# MAGIC - Account ID for the Databricks account
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
workspace_url = "https://e2-demo-field-eng.cloud.databricks.com"

# Extract account domain from workspace URL for account API
# Account domain is typically the same as workspace domain for most cases
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
print(f"🏥 Account Domain: {account_domain}")
print("⚠️ Note: Creating account-level groups requires account admin permissions")

# COMMAND ----------

# Define healthcare groups with descriptions
healthcare_groups = {
    "Healthcare_Analyst": {
        "display_name": "Healthcare Analyst",
        "description": "Population health analysts who perform cross-table analytics with deterministic masking",
        "scenarios": ["Scenario 1: Deterministic Masking"]
    },
    
    "Lab_Technician": {
        "display_name": "Lab Technician",
        "description": "Laboratory technicians with time-restricted access to lab results during business hours",
        "scenarios": ["Scenario 2: Time-Based Access Control"]
    },
    
    "External_Auditor": {
        "display_name": "External Auditor", 
        "description": "Temporary external auditors with expiring access to billing data for compliance reviews",
        "scenarios": ["Scenario 3: Policy Expiry"]
    },
    
    "Healthcare_Worker": {
        "display_name": "Healthcare Worker",
        "description": "General healthcare staff with seniority-based access to patient information",
        "scenarios": ["Scenario 4: Seniority-Based Name Masking"]
    },
    
    "Regional_Staff": {
        "display_name": "Regional Staff",
        "description": "Healthcare workers restricted to patient data within their geographic region",
        "scenarios": ["Scenario 5: Regional Data Governance"]
    },
    
    "Population_Health_Researcher": {
        "display_name": "Population Health Researcher",
        "description": "Research staff with access to age-grouped demographics for population health studies",
        "scenarios": ["Scenario 6: Age Demographics Masking"]
    },
    
    "Billing_Clerk": {
        "display_name": "Billing Clerk", 
        "description": "Billing staff with basic-level insurance verification (last 4 digits only)",
        "scenarios": ["Scenario 7: Insurance Verification - Basic Level"]
    },
    
    "Insurance_Coordinator": {
        "display_name": "Insurance Coordinator",
        "description": "Insurance processing staff with standard-level verification access", 
        "scenarios": ["Scenario 7: Insurance Verification - Standard Level"]
    },
    
    "Financial_Manager": {
        "display_name": "Financial Manager",
        "description": "Financial management staff with full insurance verification access",
        "scenarios": ["Scenario 7: Insurance Verification - Full Level"]
    },
    
    "Junior_Staff": {
        "display_name": "Junior Staff",
        "description": "Entry-level healthcare workers (residents, nursing students) with masked patient names",
        "scenarios": ["Scenario 4: Junior Level Name Masking"]
    },
    
    "Senior_Staff": {
        "display_name": "Senior Staff",
        "description": "Experienced healthcare workers with full patient name access",
        "scenarios": ["Scenario 4: Senior Level Full Access"]
    },
    
    "Department_Head": {
        "display_name": "Department Head",
        "description": "Healthcare department leadership with comprehensive access privileges",
        "scenarios": ["Multiple scenarios with elevated access"]
    }
}

print(f"📊 Prepared {len(healthcare_groups)} healthcare groups for creation")
print("\n🏥 Healthcare Groups:")
for group_name, details in healthcare_groups.items():
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
    
    # Create the group payload using Account SCIM format (per documentation)
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

# Create all healthcare account groups
print("🚀 Starting healthcare account group creation...\n")

results = {}
success_count = 0
skip_count = 0
failure_count = 0

for group_name, config in healthcare_groups.items():
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
print(f"📊 Total Groups: {len(healthcare_groups)}")

# Display created group IDs for reference
print(f"\n📋 Created Group IDs:")
for group_name, result in results.items():
    if result.get("success") and "group_id" in result:
        print(f"  • {group_name}: {result['group_id']}")

# COMMAND ----------

# Verify all account groups were created successfully
print("🔍 Verifying created healthcare account groups...\n")

try:
    list_response = requests.get(account_scim_url, headers=headers)
    
    if list_response.status_code == 200:
        all_groups = list_response.json().get('Resources', [])
        group_names = [group.get('displayName') for group in all_groups]
        
        print(f"📋 Total account groups: {len(all_groups)}")
        print("\n🏥 Healthcare account groups found:")
        
        healthcare_groups_found = []
        for group_name in healthcare_groups.keys():
            if group_name in group_names:
                healthcare_groups_found.append(group_name)
                # Find the group ID
                group_id = next((g.get('id') for g in all_groups if g.get('displayName') == group_name), 'Unknown')
                print(f"  ✅ {group_name} (ID: {group_id})")
            else:
                print(f"  ❌ {group_name} - NOT FOUND")
        
        print(f"\n📊 Healthcare account groups verification:")
        print(f"  • Found: {len(healthcare_groups_found)}/{len(healthcare_groups)}")
        
        if len(healthcare_groups_found) == len(healthcare_groups):
            print("\n🎉 All healthcare account groups created and verified successfully!")
            print("\n✅ Next Steps:")
            print("  1. Groups are now available across all workspaces in your account")
            print("  2. Assign users to groups via Databricks Admin Console or API")
            print("  3. Groups can be used in Unity Catalog ABAC policies")
        else:
            missing = set(healthcare_groups.keys()) - set(healthcare_groups_found)
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

# Display group mapping to ABAC scenarios
print("\n📋 Group to ABAC Scenario Mapping:\n")

scenario_mapping = {
    "🔐 Scenario 1: Deterministic Masking": ["Healthcare_Analyst"],
    "⏰ Scenario 2: Time-Based Access": ["Lab_Technician"],
    "📅 Scenario 3: Policy Expiry": ["External_Auditor"],
    "👥 Scenario 4: Seniority Masking": ["Junior_Staff", "Senior_Staff", "Healthcare_Worker"],
    "🌍 Scenario 5: Regional Control": ["Regional_Staff"],
    "🎂 Scenario 6: Age Demographics": ["Population_Health_Researcher"],
    "🏥 Scenario 7: Insurance Verification": ["Billing_Clerk", "Insurance_Coordinator", "Financial_Manager"]
}

for scenario, groups in scenario_mapping.items():
    print(f"\n{scenario}")
    print(f"  Groups: {', '.join(groups)}")
    for group in groups:
        if group in healthcare_groups:
            print(f"    • {group}: {healthcare_groups[group]['description'][:60]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Next Steps After Account Group Creation
# MAGIC
# MAGIC ### ✅ **Account Groups Created Successfully**
# MAGIC All 12 healthcare account groups are now available across all workspaces in your Databricks account:
# MAGIC
# MAGIC ### 📋 **Ready for ABAC Implementation:**
# MAGIC 1. **Apply Unity Catalog Tag Policies** - Run `CreateHealthcareTagPolicies.ipynb`
# MAGIC 2. **Deploy ABAC Policies** - Execute `ApplyHealthcareABACPolicies_SQL.ipynb`
# MAGIC 3. **Assign Users to Groups** - Add users to appropriate account groups
# MAGIC 4. **Test Scenarios** - Validate each of the 7 ABAC scenarios
# MAGIC
# MAGIC ### 👥 **User Assignment Options:**
# MAGIC - **Databricks Account Console** - Assign users to account groups via Admin Console
# MAGIC - **Account SCIM API** - Programmatic user assignment to account groups
# MAGIC - **Identity Provider Integration** - Automated user provisioning via SSO
# MAGIC
# MAGIC ### 🔐 **ABAC Policy Binding:**
# MAGIC The ABAC policies in `ApplyHealthcareABACPolicies_SQL.ipynb` will now work with these account groups:
# MAGIC - Policies use `TO 'Group_Name'` syntax to bind to these account groups
# MAGIC - Tag-based conditions will evaluate account group membership
# MAGIC - Row filters and column masks will apply based on account group assignments
# MAGIC
# MAGIC ### 📊 **Account vs Workspace Groups:**
# MAGIC - **Account Groups** (what we created): Available across all workspaces
# MAGIC - **Workspace Groups**: Local to individual workspaces only
# MAGIC - **Unity Catalog ABAC**: Works with both account and workspace groups
# MAGIC
# MAGIC ## 🏥 Healthcare ABAC Account Groups Ready! 🎉
# MAGIC
# MAGIC Your Databricks account now has all the required groups for comprehensive healthcare data governance using Unity Catalog ABAC policies across all workspaces.
# MAGIC
# MAGIC ---