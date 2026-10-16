# Databricks notebook source
# MAGIC %md
# MAGIC # 🏷️ Finance ABAC Tag Policies Creation
# MAGIC
# MAGIC This notebook creates comprehensive Unity Catalog tag policies for finance ABAC scenarios using Databricks REST API.
# MAGIC
# MAGIC ## 📋 Prerequisites
# MAGIC - Databricks workspace with Unity Catalog enabled
# MAGIC - Account admin or user with CREATE permission for tag policies
# MAGIC - Personal Access Token with appropriate permissions
# MAGIC
# MAGIC ## 🎯 Tag Policies to Create (11 Total)
# MAGIC 1. **pci_clearance** - PCI-DSS access levels for payment card data
# MAGIC 2. **payment_role** - Payment processing roles
# MAGIC 3. **aml_clearance** - AML investigation clearance levels
# MAGIC 4. **trading_desk** - Trading desk assignment
# MAGIC 5. **information_barrier** - Chinese wall classification
# MAGIC 6. **data_residency** - Geographic data residency requirements
# MAGIC 7. **customer_region** - Customer data geographic location
# MAGIC 8. **market_hours** - Trading hours access control
# MAGIC 9. **audit_project** - Specific audit project identification
# MAGIC 10. **pii_level** - Personal information access classification
# MAGIC 11. **sox_scope** - SOX audit scope classification

# COMMAND ----------

# Import required libraries
import requests
import json
from typing import List, Dict, Any

# COMMAND ----------

# Configuration - Update these values for your environment
workspace_url = "https://dbc-0f56e540-7f65.cloud.databricks.com"  # Update with your workspace URL

# Get token from Databricks secrets or environment
# Option 1: From dbutils (if running in Databricks)
try:
    token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
    print("✅ Token retrieved from Databricks context")
except:
    print("✅ Token can't be retrieved from configuration")

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
            print(f"   🏷️ Allowed values ({len(allowed_values)}): {', '.join(allowed_values[:5])}{'...' if len(allowed_values) > 5 else ''}")
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

# Define all finance tag policies
finance_tag_policies = {
    "pci_clearance": {
        "values": [
            "Basic",
            "Standard",
            "Full",
            "Administrative"
        ],
        "description": "PCI-DSS access levels: Basic=last4, Standard=masked, Full=complete card data, Administrative=all cardholder data"
    },
    
    "payment_role": {
        "values": [
            "Customer_Service",
            "Fraud_Analyst",
            "Compliance_Officer",
            "Payment_Processor"
        ],
        "description": "Payment processing roles for PCI-DSS access control"
    },
    
    "aml_clearance": {
        "values": [
            "Junior_Analyst",
            "Senior_Investigator",
            "Compliance_Officer",
            "FinCEN_Reporter"
        ],
        "description": "AML investigation clearance levels for progressive data access (AML/KYC, FATF compliance)"
    },
    
    "trading_desk": {
        "values": [
            "Equity",
            "Fixed_Income",
            "FX",
            "Commodities",
            "Research",
            "Risk_Management"
        ],
        "description": "Trading desk assignment for position data access control"
    },
    
    "information_barrier": {
        "values": [
            "Trading_Side",
            "Advisory_Side",
            "Neutral"
        ],
        "description": "Chinese wall information barrier classification (SEC, MiFID II compliance)"
    },
    
    "data_residency": {
        "values": [
            "EU",
            "US",
            "APAC",
            "LATAM",
            "Global"
        ],
        "description": "Geographic data residency requirements for GDPR, CCPA, PDPA compliance"
    },
    
    "customer_region": {
        "values": [
            "EU",
            "US",
            "APAC",
            "LATAM"
        ],
        "description": "Customer data geographic location for regional data access control"
    },
    
    "market_hours": {
        "values": [
            "Trading_Hours",
            "After_Hours",
            "Weekend",
            "24x7"
        ],
        "description": "Market hours-based access control for trading positions (prevent manipulation during trading)"
    },
    
    "audit_project": {
        "values": [
            "Q1_SOX_Audit",
            "Q2_SOX_Audit",
            "Q3_SOX_Audit",
            "Q4_SOX_Audit",
            "Annual_Financial_Audit",
            "Regulatory_Review",
            "Internal_Audit"
        ],
        "description": "Specific audit project identification for temporary access control (SOX compliance)"
    },
    
    "pii_level": {
        "values": [
            "Full_PII",
            "Limited_PII",
            "De_Identified",
            "Statistical_Only"
        ],
        "description": "Personal information access classification for GDPR, GLBA, CCPA privacy compliance"
    },
    
    "sox_scope": {
        "values": [
            "In_Scope",
            "Out_Of_Scope"
        ],
        "description": "SOX audit scope classification for financial reporting controls"
    }
}

print(f"📊 Prepared {len(finance_tag_policies)} finance tag policies for creation")

# COMMAND ----------

import time

# Create all finance tag policies
print("🚀 Starting finance tag policy creation...\n")

results = {}
success_count = 0
failure_count = 0

for tag_key, config in finance_tag_policies.items():
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
    time.sleep(1.5)
print(f"\n{'='*60}")
print("📊 CREATION SUMMARY")
print(f"{'='*60}")
print(f"✅ Successful: {success_count}")
print(f"❌ Failed: {failure_count}")
print(f"📊 Total: {len(finance_tag_policies)}")

# COMMAND ----------

# List all created tag policies for verification
print("🔍 Verifying created tag policies...\n")

try:
    list_response = requests.get(base_url, headers=headers)
    
    if list_response.status_code == 200:
        policies = list_response.json()
        
        print(f"📋 Found {len(policies.get('tag_policies', []))} tag policies in Unity Catalog:")
        print("\n" + "="*80)
        
        finance_policies = []
        for policy in policies.get('tag_policies', []):
            key = policy.get('key', 'Unknown')
            description = policy.get('description', 'No description')
            values = [v.get('name', '') for v in policy.get('values', [])]
            
            # Check if this is one of our finance policies
            if key in finance_tag_policies:
                finance_policies.append(key)
                print(f"🏦 {key}")
                print(f"   📝 Description: {description}")
                print(f"   🏷️ Values ({len(values)}): {', '.join(values[:5])}{'...' if len(values) > 5 else ''}")
                print()
        
        print(f"\n✅ Finance tag policies found: {len(finance_policies)}/{len(finance_tag_policies)}")
        
        if len(finance_policies) == len(finance_tag_policies):
            print("🎉 All finance tag policies created successfully!")
        else:
            missing = set(finance_tag_policies.keys()) - set(finance_policies)
            print(f"⚠️ Missing policies: {missing}")
    
    else:
        print(f"❌ Failed to list tag policies. Status: {list_response.status_code}")
        print(f"Response: {list_response.text}")

except Exception as e:
    print(f"❌ Exception while listing tag policies: {str(e)}")

# COMMAND ----------

# Generate sample tag application SQL for reference
print("📋 Sample SQL for applying tags to finance tables:\n")

sample_sql = '''
-- Use the finance catalog and schema
USE CATALOG fincat;
USE SCHEMA finance;

-- Example: Apply PCI-DSS tags to CreditCards table
ALTER TABLE CreditCards 
SET TAGS (
    'pci_clearance' = 'Full',
    'payment_role' = 'Fraud_Analyst'
);

-- Example: Apply PCI tags to sensitive card columns
ALTER TABLE CreditCards ALTER COLUMN CardNumber
SET TAGS (
    'pci_clearance' = 'Full',
    'payment_role' = 'Fraud_Analyst'
);

ALTER TABLE CreditCards ALTER COLUMN CVV
SET TAGS (
    'pci_clearance' = 'Administrative'
);

-- Example: Apply AML tags to Transactions table
ALTER TABLE Transactions
SET TAGS (
    'aml_clearance' = 'Senior_Investigator'
);

-- Example: Apply Chinese wall tags to TradingPositions
ALTER TABLE TradingPositions
SET TAGS (
    'trading_desk' = 'Equity',
    'information_barrier' = 'Trading_Side'
);

-- Example: Apply data residency tags to Customers
ALTER TABLE Customers
SET TAGS (
    'data_residency' = 'Global',
    'pii_level' = 'Full_PII'
);

ALTER TABLE Customers ALTER COLUMN CustomerRegion
SET TAGS (
    'customer_region' = 'EU'
);

-- Verify tag assignments
SELECT table_name, tag_name, tag_value
FROM system.information_schema.table_tags 
WHERE schema_name = 'finance'
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
# MAGIC 2. **Apply tags to tables** using `3.ApplyFinanceSetTags.sql`
# MAGIC 3. **Create ABAC policies** using `4.CreateFinanceABACPolicies.sql`
# MAGIC 4. **Test access control** with different user personas and tag assignments
# MAGIC
# MAGIC ## 📚 Tag Policy Summary
# MAGIC
# MAGIC ### Payment & Card Security (PCI-DSS)
# MAGIC - `pci_clearance` - 4 levels from Basic to Administrative
# MAGIC - `payment_role` - Payment processing team roles
# MAGIC
# MAGIC ### AML & Compliance
# MAGIC - `aml_clearance` - Progressive AML investigation access
# MAGIC - `sox_scope` - SOX audit scope classification
# MAGIC - `audit_project` - Temporary auditor access projects
# MAGIC
# MAGIC ### Trading & Markets
# MAGIC - `trading_desk` - Trading desk assignments
# MAGIC - `information_barrier` - Chinese wall enforcement
# MAGIC - `market_hours` - Time-based trading access
# MAGIC
# MAGIC ### Privacy & Residency
# MAGIC - `pii_level` - Personal information classification
# MAGIC - `data_residency` - Geographic data hosting requirements
# MAGIC - `customer_region` - Customer data geographic location
# MAGIC
# MAGIC ## 🏦 Finance ABAC Demo Ready!
# MAGIC
# MAGIC Your Unity Catalog is now equipped with comprehensive tag policies for enterprise financial services data governance! 🎉
