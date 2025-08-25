---
title: "Feature Registry Application"
language: Python
author: "Yang Cheng"
date: 2025-08-05
---

# 🚀 Feature Registry Application

This is a modern web application that allows users to interact with the Databricks Feature Registry. The app provides a user-friendly interface for exploring existing features in Unity Catalog. Additionally, users can generate code for creating feature specs and training sets to train machine learning models and deploy features as Feature Serving Endpoints.

## ✨ Features

- 🔍 List and search for features in Unity Catalog
- 🔒 On-behalf-of-user authentication
- ⚙️ Code-gen for creating feature specs and training sets
- 📋 Configurable catalog allow-listing for access control

## 🏗️ Architecture

The application is built with:
- 🌟 **Streamlit** for the UI
- 🧱 **Databricks SDK** for interacting with Unity Catalog

## 📸 Example Interface

![Feature Registry Interface](./images/feature-registry-interface.png)

## 🚀 Deployment

### Create an App
1. Log into your destination Databricks workspace and navigate to "Compute > Apps"
2. Click on "Create App" and select "Create a custom app"
3. Enter an app name and click "Create app"

### Customization
1. Create a file named `deploy_config.sh` in the root folder with the following variables:
   ```sh
   # Path to a destination folder in default Databricks workspace where source code will be sync'ed
   export DEST=/Workspace/Users/Path/To/App/Code 
   # Name of the App to deploy
   export APP_NAME=your-app-name
   ```
   Or simply run `./deploy.sh` - it will create a template file if it doesn't exist

2. Update `deploy_config.sh` with the config for your environment

3. Ensure the Databricks CLI is installed and configured on your machine. The "DEFAULT" profile should point to the destination workspace where the app will be deployed. You can find instructions here for [AWS](https://docs.databricks.com/dev-tools/cli/index.html) / [Azure](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/cli/)

### Deploy the App
1. Navigate to the app directory
2. Run `./deploy.sh` shell command. This will sync the app code to the destination workspace location and deploy the app
3. Navigate to the Databricks workspace and access the app via "Compute > Apps"

## 🔐 Access Control

### Catalog Allow-Listing

By default, the Feature Registry App will show all the catalogs to which the user has read access. You can restrict which Unity Catalog catalogs users can explore for features. This is useful for:
- Limiting feature discovery to production-ready catalogs
- Ensuring data scientists only access approved feature sets
- Organizing features by teams or projects

#### Setting Up Allow-Listed Catalogs

1. Edit the `src/uc_catalogs_allowlist.yaml` file
2. Uncomment and add the catalog names you want to allow:

   ```yaml
   # List catalogs that should be accessible in the Feature Registry App
   - production_features
   - team_a_catalog
   - ml_features_catalog
   ```

3. If the file is empty or all entries are commented out, the app will show all catalogs available to the user
4. Deploy the app with the updated configuration

**Note:** Users will still need appropriate permissions in Unity Catalog to access the data within these catalogs. The allow-list acts as an additional filter on top of existing permissions.

## 🔑 Requirements

The application requires the following scopes:
- `catalog.catalogs:read`
- `catalog.schemas:read`
- `catalog.tables:read` 

The app owner needs to grant other users `Can Use` permission for the app itself, along with access to the underlying Databricks resources.
