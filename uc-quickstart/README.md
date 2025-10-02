---
title: "Unity Catalog Quickstart"
language: HCL
author: "Louis Chen, Abhishek Pratap Singh, Renji Luke Harold, Rosalie Noel, Junchi Liu"
date: 2025-08-15

tags: 
- Unity Catalog
- Automation

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

2. **Configure the ```terraform.tfvars``` by referring to the ```template.tfvars.example```:**

   Copy the example file and customize it with your specific values.

3. **Configure for Your Cloud Provider:**

- Navigate into the appropriate directory (`aws` or `azure`) based on your cloud provider.
- Follow specific instructions detailed in the README within that folder.

4. **Initialize Terraform:**

   Run this command to fetch necessary Terraform providers and modules:

   ```bash
   terraform init
   ```


5. **Deploy Unity Catalog:**

   Execute the following command to apply your Terraform configuration:

   ```bash
   terraform apply
   ```

### ✅ Verify Deployment

Once deployment is complete, verify the setup directly within your Databricks workspace to ensure all components are correctly configured.


## 📄 License

This project is licensed under the Databricks License—see [LICENSE](../LICENSE) for full details.

