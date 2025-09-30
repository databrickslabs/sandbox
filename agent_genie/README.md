# Conversational Agent App

**Language:** Python  
**Author:** Nitin Aggarwal  
**Date:** 2025-09-19  

## Conversational Agent App

This repository demonstrates how to integrate Databricks' AI/BI Genie Conversation APIs into custom Databricks Apps applications, allowing users to interact with their structured data using natural language.

You can also click the Generate insights button and generate deep analysis and trends of your data. 

---

## Overview
This app is a Python-based application (using FastAPI) featuring a chat interface powered by Databricks Genie Conversation APIs, built specifically to run as a custom Databricks App. This integration showcases how to leverage Databricks' platform capabilities to create interactive data applications with minimal infrastructure overhead.

The Databricks Genie Conversation APIs enable you to embed AI/BI Genie capabilities into any application, allowing users to:
- Ask questions about their data in natural language
- Get SQL-powered insights without writing code
- Follow up with contextual questions in a conversation thread

---

## Key Features
- **Powered by Databricks Apps**: Deploy and run directly from your Databricks workspace with built-in security and scaling  
- **Zero Infrastructure Management**: Leverage Databricks Apps to handle hosting, scaling, and security  
- **Workspace Integration**: Access your data assets and models directly from your Databricks workspace  
- **Natural Language Data Queries**: Ask questions about your data in plain English  
- **Stateful Conversations**: Maintain context for follow-up questions  
- **OBO (On-Behalf-Of) Authentication**: User credentials passthrough for fine-grained access control  

---

## Example Use Case
This app shows how to create a simple interface that connects to the Genie API, allowing users to:
1. Start a conversation with a question about their supply chain data  
2. View generated SQL and results  
3. Ask follow-up questions that maintain context  

---

## Installation & Usage

### Prerequisites
- Python 3.9+  
- Databricks workspace access with Genie APIs enabled  
- `pip` package manager  

### Setup Locally
1. Clone the repository:
   ```bash
   git clone [<your_repo_url>](https://github.com/nitinaggarwal-databricks/sandbox/tree/0e5d157b6a653cc05dd61e9619ac156d07689dce/agent_genie)
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app locally:
   ```bash
   python app.py
   ```

5. Open your browser at [http://localhost:8000](http://localhost:8000) to interact with the chat interface.

### Running in Databricks
Refer to the [Deploying to Databricks Apps](#deploying-to-databricks-apps) section below.

---

## Project Structure
```
agent-genie/
│
├── agent_genie/
│   ├── app.py                 # Main entry point for the Dash/Flask app
│   ├── helper.py              # Utility functions
│   ├── table_extraction.py    # Table data parsing and extraction logic
│   ├── tracking.py            # Event logging and tracking
│   ├── manual_ai_content.py   # Predefined AI responses/content
│   ├── requirements.txt       # Python dependencies
│   ├── templates/
│   │   └── index.html         # Frontend UI template
│   ├── app.yaml               # App configuration
│   ├── databricks.yml         # Databricks-specific config
│   └── ...
│
├── manifest.yaml              # High-level manifest
└── manifest.mf                # App metadata
```

---

## Deploying to Databricks Apps
The app can be installed through Databricks Marketplace. If you prefer to clone and deploy it manually, please refer to these instructions:

1. Clone the repository to your Databricks workspace using Git Folder:
   - Navigate to the Workspace section in the sidebar.  
   - Click on the 'Create' button, select the 'Git Folder' option and follow the prompts to clone the repository.  

2. Create an app with a serving endpoint resource:
   - Navigate to the Compute section in the sidebar.  
   - Go to the Apps tab and click the **Create app** button. Fill in the necessary fields and click **Next: Configuration**.  
   - To reuse an existing app, click the link to your app in the Name column to go to the detail page, then click **Edit**.  
   - In the **App resources** section, click **+ Add resource** and select **Serving endpoint**. Choose a chat endpoint, grant `CAN_QUERY` permission and name it `serving_endpoint`.  
   - Select Genie Space, grant `CAN_RUN` permission and name it `genie_space`.  

3. Deploy the app using the Databricks Apps interface:
   - Go to the detail page of the app.  
   - Click **Deploy** and select the folder `conversational-agent-app` from the created Git folder.  
   - Click **Select**, then **Deploy**.  
   - Review the configuration and click **Deploy**.  

For more details, refer to the official Databricks documentation.  

---

## Troubleshooting
- After installing the app from Marketplace, check the **Authorization page** for API scope details.  
- When you open the URL link for the first time, ensure you see the OBO scope authorization page with all four scopes:  
  - `serving.serving-endpoints`  
  - `dashboards.genie`  
  - `files.files`  
  - `sql`  

If you cloned the Git repo directly, note that `serving.serving-endpoints` may not yet appear in the scope list in the UI. You will need to use the Databricks API or CLI to manually grant this scope.  

Example CLI update:  
```bash
databricks account custom-app-integration update '65d90ec2-54ba-4fcb-a85d-eac774235aea' --json '{"scopes": ["openid", "profile", "email", "all-apis", "offline_access", "serving.serving-endpoints"]}'
```

Other common fixes:  
- Clear browser cookies or try incognito mode if scopes don’t refresh  
- Ensure users have proper access to underlying resources:  
  - **Tables**: `USE CATALOG`, `USE SCHEMA`, `SELECT` permissions  
  - **Genie Space**: `CAN_RUN` permission  
  - **SQL Warehouse**: `CAN_USE` permission  
  - **Model Serving Endpoint**: `CAN_QUERY` permission  

---

## Resources
- [Databricks Genie Documentation](https://docs.databricks.com/)  
- [Conversation APIs Documentation](https://docs.databricks.com/)  
- [Databricks Apps Documentation](https://docs.databricks.com/)  
