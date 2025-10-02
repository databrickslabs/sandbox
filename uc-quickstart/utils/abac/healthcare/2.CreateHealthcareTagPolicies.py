# Databricks notebook source
# MAGIC %md
# MAGIC # 🏷️ Healthcare ABAC Tag Policies Creation
# MAGIC
# MAGIC This notebook creates comprehensive Unity Catalog tag policies for 7 healthcare ABAC scenarios using Databricks REST API.
# MAGIC
# MAGIC ## 📋 Prerequisites
# MAGIC - Databricks workspace with Unity Catalog enabled
# MAGIC - Account admin or user with CREATE permission for tag policies
# MAGIC - Personal Access Token with appropriate permissions
# MAGIC
# MAGIC ## 🎯 Tag Policies to Create
# MAGIC 1. **job_role** - Healthcare worker role classification
# MAGIC 2. **data_purpose** - Intended use purpose for data access
# MAGIC 3. **shift_hours** - Time-based access control
# MAGIC 4. **access_expiry_date** - Temporal access control with expiration
# MAGIC 5. **seniority** - Healthcare worker experience level
# MAGIC 6. **region** - Geographic data residency control
# MAGIC 7. **research_approval** - Research study approval level
# MAGIC 8. **phi_level** - Protected Health Information access classification
# MAGIC 9. **data_residency** - Geographic data residency requirements
# MAGIC 10. **verification_level** - Insurance/billing verification access level
# MAGIC 11. **audit_project** - Specific audit project identification

# COMMAND ----------

# Import required libraries
import requests
import json
from typing import List, Dict, Any
import os
# COMMAND ----------
# Configuration - Use environment variable for workspace URL
workspace_url = os.environ.get("DATABRICKS_WORKSPACE_URL")
if not workspace_url:
    # Optionally, you can set a default or raise an error
    workspace_url = "https://e2-demo-field-eng.cloud.databricks.com"
    print("⚠️  DATABRICKS_WORKSPACE_URL not set. Using default demo workspace URL. Update this for your environment.")

# Get token from Databricks secrets or environment
# Option 1: From dbutils (if running in Databricks)
try:
    token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
    print("✅ Token retrieved from Databricks context")
except:
  
    
    print("✅ Token cant be retrieved from configuration")

# Setup API headers and base URL
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
base_url = f"{workspace_url}/api/2.0/tag-policies"
print(f"🌐 Base URL: {base_url}")

# COMMAND ----------

# Utility function to create tag policy
def create_tag_policy(tag_key: str, allowed_values: List[str], description: str) -> Dict[str, Any]:
    """
    Create a Unity Catalog tag policy using REST API
    
    Args:
        tag_key: The tag key name (case sensitive)
        allowed_values: List of allowed values for this tag
        description: Description of the tag policy
    
    Returns:
        API response as dictionary
    """
    
    # First, try to delete existing tag policy (if exists)
    delete_url = f"{base_url}/{tag_key}"
    try:
        delete_response = requests.delete(delete_url, headers=headers)
        if delete_response.status_code == 200:
            print(f"🗑️ Deleted existing tag policy: {tag_key}")
    except Exception as e:
        print(f"ℹ️ No existing tag policy to delete for: {tag_key}")
    
    # Create the tag policy payload
    create_payload = {
        "tag_policy": {
            "key": tag_key,
            "values": [{"name": value} for value in allowed_values],
            "description": description
        }
    }
    
    # Make the API call to create tag policy
    try:
        create_response = requests.post(base_url, headers=headers, data=json.dumps(create_payload))
        
        if create_response.status_code == 200:
            print(f"✅ Successfully created tag policy: {tag_key}")
            print(f"   📝 Description: {description}")
            print(f"   🏷️ Allowed values: {allowed_values}")
            return {"success": True, "response": create_response.json()}
        else:
            print(f"❌ Failed to create tag policy: {tag_key}")
            print(f"   Status Code: {create_response.status_code}")
            print(f"   Response: {create_response.text}")
            return {"success": False, "error": create_response.text}
    
    except Exception as e:
        print(f"❌ Exception creating tag policy {tag_key}: {str(e)}")
        return {"success": False, "error": str(e)}

# COMMAND ----------

# Define all healthcare tag policies
healthcare_tag_policies = {
    "job_role": {
        "values": [
            "Healthcare_Analyst",
            "Lab_Technician",
            "External_Auditor",
            "Healthcare_Worker",
            "Regional_Staff",
            "Population_Health_Researcher",
            "Billing_Clerk",
            "Insurance_Coordinator",
            "Financial_Manager",
            "Junior_Staff",
            "Senior_Staff",
            "Department_Head"
        ],
        "description": "Healthcare worker role classification for ABAC access control"
    },
    
    "data_purpose": {
        "values": [
            "Population_Analytics",
            "Clinical_Care",
            "Financial_Operations",
            "Research_Study",
            "Audit_Review"
        ],
        "description": "Intended use purpose for data access"
    },
    
    "shift_hours": {
        "values": [
            "Standard_Business",
            "Extended_Hours", 
            "Night_Shift",
            "Emergency_24x7"
        ],
        "description": "Time-based access control for healthcare operations (Standard_Business=8AM-6PM)"
    },
    
    "access_expiry_date": {
        "values": [
            "2025-12-31",
            "2026-03-31",
            "2026-06-30", 
            "2026-12-31",
            "Permanent"
        ],
        "description": "Temporal access control with expiration dates for temporary staff and auditors"
    },
    
    "seniority": {
        "values": [
            "Junior_Staff",
            "Mid_Level_Staff",
            "Senior_Staff",
            "Department_Head", 
            "Chief_Medical_Officer"
        ],
        "description": "Healthcare worker experience and access level for progressive data access"
    },
    
    "region": {
        "values": [
            "North",
            "South",
            "East",
            "West",
            "Central",
            "National"
        ],
        "description": "Geographic data residency and access control for multi-location healthcare systems"
    },
    
    "research_approval": {
        "values": [
            "Demographics_Study",
            "Clinical_Outcomes_Research",
            "Population_Health_Study",
            "Quality_Improvement",
            "IRB_Approved_Research"
        ],
        "description": "Research study approval and data access level for HIPAA-compliant research"
    },
    
    "phi_level": {
        "values": [
            "Full_PHI",
            "Limited_Dataset", 
            "De_Identified",
            "Statistical_Only"
        ],
        "description": "Protected Health Information access classification per HIPAA requirements"
    },
    
    "data_residency": {
        "values": [
            "Regional_Boundary",
            "State_Boundary",
            "National_Only",
            "Cross_Border_Approved"
        ],
        "description": "Geographic data residency requirements for compliance with state and federal laws"
    },
    
    "verification_level": {
        "values": [
            "Basic",
            "Standard",
            "Full",
            "Administrative"
        ],
        "description": "Insurance and billing verification access level (Basic=last4 digits, Full=complete)"
    },
    
    "audit_project": {
        "values": [
            "Q4_Compliance_Review",
            "Annual_Financial_Audit",
            "HIPAA_Assessment",
            "Quality_Assurance_Review"
        ],
        "description": "Specific audit project identification for temporary access control"
    }
}

print(f"📊 Prepared {len(healthcare_tag_policies)} healthcare tag policies for creation")

# COMMAND ----------

# Create all healthcare tag policies
print("🚀 Starting healthcare tag policy creation...\n")

results = {}
success_count = 0
failure_count = 0

for tag_key, config in healthcare_tag_policies.items():
    print(f"\n{'='*60}")
    print(f"Creating tag policy: {tag_key}")
    print(f"{'='*60}")
    
    result = create_tag_policy(
        tag_key=tag_key,
        allowed_values=config["values"],
        description=config["description"]
    )
    
    results[tag_key] = result
    
    if result["success"]:
        success_count += 1
    else:
        failure_count += 1
    
    print("\n")

print(f"\n{'='*60}")
print("📊 CREATION SUMMARY")
print(f"{'='*60}")
print(f"✅ Successful: {success_count}")
print(f"❌ Failed: {failure_count}")
print(f"📊 Total: {len(healthcare_tag_policies)}")

# COMMAND ----------

# List all created tag policies for verification
print("🔍 Verifying created tag policies...\n")

try:
    list_response = requests.get(base_url, headers=headers)
    
    if list_response.status_code == 200:
        policies = list_response.json()
        
        print(f"📋 Found {len(policies.get('tag_policies', []))} tag policies in Unity Catalog:")
        print("\n" + "="*80)
        
        healthcare_policies = []
        for policy in policies.get('tag_policies', []):
            key = policy.get('key', 'Unknown')
            description = policy.get('description', 'No description')
            values = [v.get('name', '') for v in policy.get('values', [])]
            
            # Check if this is one of our healthcare policies
            if key in healthcare_tag_policies:
                healthcare_policies.append(key)
                print(f"🏥 {key}")
                print(f"   📝 Description: {description}")
                print(f"   🏷️ Values ({len(values)}): {', '.join(values[:5])}{'...' if len(values) > 5 else ''}")
                print()
        
        print(f"\n✅ Healthcare tag policies found: {len(healthcare_policies)}/{len(healthcare_tag_policies)}")
        
        if len(healthcare_policies) == len(healthcare_tag_policies):
            print("🎉 All healthcare tag policies created successfully!")
        else:
            missing = set(healthcare_tag_policies.keys()) - set(healthcare_policies)
            print(f"⚠️ Missing policies: {missing}")
    
    else:
        print(f"❌ Failed to list tag policies. Status: {list_response.status_code}")
        print(f"Response: {list_response.text}")

except Exception as e:
    print(f"❌ Exception while listing tag policies: {str(e)}")

# COMMAND ----------

# Generate sample tag application SQL for reference
print("📋 Sample SQL for applying tags to healthcare tables:\n")

sample_sql = '''
-- Use the healthcare catalog and schema
USE CATALOG apscat;
USE SCHEMA healthcare;

-- Example: Apply job_role and data_purpose tags to Patients table
ALTER TABLE Patients 
SET TAGS (
    'job_role' = 'Healthcare_Analyst',
    'data_purpose' = 'Population_Analytics',
    'phi_level' = 'De_Identified'
);

-- Example: Apply seniority-based tags to patient name columns
ALTER TABLE Patients ALTER COLUMN FirstName
SET TAGS (
    'seniority' = 'Senior_Staff',
    'job_role' = 'Healthcare_Worker'
);

-- Example: Apply temporal access tags to LabResults
ALTER TABLE LabResults
SET TAGS (
    'shift_hours' = 'Standard_Business',
    'job_role' = 'Lab_Technician'
);

-- Verify tag assignments
SELECT table_name, tag_name, tag_value
FROM system.information_schema.table_tags 
WHERE table_schema = 'healthcare'
ORDER BY table_name, tag_name;
'''

print(sample_sql)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🎯 Next Steps
# MAGIC
# MAGIC After running this notebook successfully:
# MAGIC
# MAGIC 1. **Verify tag policies** are created in Databricks Account Console → Data → Tag Policies
# MAGIC 2. **Apply tags to tables** using the SQL commands from `unity_catalog_tag_policies.sql`
# MAGIC 3. **Create ABAC policies** using the masking functions from `comprehensive_abac_functions.sql`
# MAGIC 4. **Test access control** with different user personas and tag assignments
# MAGIC
# MAGIC ## 📚 Related Files
# MAGIC
# MAGIC - `abac_demo_plan.txt` - Detailed 7-scenario blueprint
# MAGIC - `unity_catalog_tag_policies.sql` - Complete SQL for tag application
# MAGIC - `comprehensive_abac_functions.sql` - Masking and row filter functions
# MAGIC - `tag_policy_implementation_guide.md` - Step-by-step implementation guide
# MAGIC
# MAGIC ## 🏥 Healthcare ABAC Demo Ready!
# MAGIC
# MAGIC Your Unity Catalog is now equipped with comprehensive tag policies for enterprise healthcare data governance! 🎉