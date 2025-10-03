# Databricks Unity Catalog Quickstart 🌐🚀

**Accelerate Your Unity Catalog Setup with Optimized Terraform Automation!**

Welcome to the **databricks-uc-quickstart** repository! This project helps you deploy Unity Catalog (UC) on Databricks swiftly and efficiently, using Terraform scripts pre-configured with recommended settings. Eliminate tedious setup and configuration overhead to quickly launch your data governance initiatives.

## 📋 Best Practices Enforced

This quickstart enforces the following Unity Catalog best practices:

- **Catalog Design Defaults**: Pre-configured catalog structures optimized for data governance
- **Workspace Defaults**: Standard workspace configurations for consistent deployments
- **Role Permission Defaults**: Pre-defined role-based access controls following least privilege principles
- **Storage Setup Defaults**: Optimized storage configurations for Unity Catalog
- **Data Sharing Defaults**: Secure data sharing configurations ready for collaboration
- **Research UC Default and Compatibility**: Ensures compatibility with existing Databricks features
- **Volume Defaults**: Standard volume configurations for data storage
- **Enable System Tables and Grant Role Access**: Automatic system table enablement with appropriate role permissions

Additionally, this quickstart includes **Industry Templates for ABAC** (Attribute-Based Access Control) implemented through Python and SQL notebooks, allowing users to leverage industry-ready functions and policies for fine-grained access control.

The Terraform configurations can be customized by modifying the variables in your deployment, while ABAC policies are managed through the provided notebooks.

## 🌟 Key Benefits

- **Automated Terraform Deployment**: Effortlessly set up and manage Unity Catalog.
- **Instant Setup**: Deploy UC with recommended default configurations.
- **Reduced Boilerplate**: Minimal setup—focus more on your core data projects.
- **Flexible & Customizable**: Easily adapt configurations to match your unique requirements.

## 🏗️ What Gets Deployed

This Terraform quickstart deploys a complete Unity Catalog environment with the following components:

### **Core Infrastructure**
- **3 Unity Catalog Environments**: Production, Development, and Sandbox catalogs
- **Cloud Storage**: Dedicated storage accounts/buckets for each catalog with proper IAM/RBAC
- **External Locations**: Secure storage credential and external location mappings
- **System Schemas**: Access, billing, compute, and storage system tables (if permissions allow)

### **Access Management**
- **User Groups**: Production service principals, developers, and sandbox users
- **Catalog Permissions**: Role-based access control with environment-specific privileges
- **System Schema Grants**: Appropriate permissions for monitoring and governance

### **Compute Resources**
- **Cluster Policies**: Environment-specific policies with cost controls and security settings
- **Clusters**: Pre-configured clusters for each environment with proper access controls

### **Cloud-Specific Resources**

**AWS Deployment:**
- S3 buckets with versioning and encryption
- IAM roles and policies for Unity Catalog access
- Cross-account trust relationships

**Azure Deployment:**
- Storage accounts with containers
- Managed identities and access connectors
- RBAC assignments for Databricks integration

## 🚀 Quick Start

Follow these steps to rapidly deploy Unity Catalog using Terraform:

### 📌 Prerequisites

Ensure you have:

- A Databricks Account
- [Terraform Installed](https://developer.hashicorp.com/terraform/downloads)
- Basic knowledge of Databricks and Terraform

**Workspace Requirements:**
- An existing Databricks workspace is required
- Workspace ID must be provided in the Terraform configuration (see template.tfvars.example)
- The quickstart will configure Unity Catalog resources and permissions within your existing workspace

### 🛠 Installation Steps

1. **Clone this Repository:**

   ```bash
   git clone https://github.com/databrickslabs/sandbox.git
   cd sandbox/uc-quickstart/
   ```

2. **Choose Your Cloud Provider:**
   
   Navigate to the appropriate directory based on your cloud provider:
   
   **For AWS:**
   ```bash
   cd aws/
   ```
   
   **For Azure:**
   ```bash
   cd azure/
   ```

3. **Follow Cloud-Specific Setup:**
   
   Each cloud provider has specific prerequisites and configuration steps detailed in their respective README files:
   - [AWS Setup Instructions](aws/README.md)
   - [Azure Setup Instructions](azure/README.md)

### ✅ Verify Deployment

Once deployment is complete, verify the setup directly within your Databricks workspace to ensure all components are correctly configured.

## 🔧 Need Help?

For cloud-specific troubleshooting and detailed configuration help:
- **AWS Issues:** See [AWS README](aws/README.md#troubleshooting)
- **Azure Issues:** See [Azure README](azure/README.md#troubleshooting)
- **General Questions:** Check the [main documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)

## 📄 License

This project is licensed under the Databricks License—see [LICENSE](../LICENSE) for full details.

