# Databricks notebook source
# MAGIC %md
# MAGIC # External Model - Azure OpenAI Setup
# MAGIC This notebook sets up an external model endpoint for Azure OpenAI in Databricks.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Ensure that the Supported models like `gpt-4` mentioned in [this document](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/external-models/) are available in your Azure OpenAI service.
# MAGIC - You have deployed an Azure OpenAI model. For deployment instructions, refer to the [Azure OpenAI deployment documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal).
# MAGIC - You have the following information for parameters available:
# MAGIC   - Your Azure OpenAI API key
# MAGIC   - The base URL for your Azure OpenAI API service
# MAGIC   - The deployment name of your Azure OpenAI model
# MAGIC   - The latest API version for Azure OpenAI (e.g., `2024-05-01-preview`)
# MAGIC
# MAGIC ## Parameters
# MAGIC | Parameter Name | Required | Description | Example |
# MAGIC |----------------|----------|-------------|---------|
# MAGIC | endpoint_name | Yes | Name for the new Databricks serving endpoint | `my-azure-openai-endpoint` |
# MAGIC | model_name | Yes | Name of the external model | `gpt-4o` |
# MAGIC | openai_api_key | Yes | Azure OpenAI API Key for authentication | ***your-api-key*** |
# MAGIC | openai_api_base | Yes | Base URL for the Azure OpenAI API service | `https://oneenvazureopenai.openai.azure.com` |
# MAGIC | openai_api_version | Yes | Version of the Azure OpenAI service to use | `2024-05-01-preview` |
# MAGIC | openai_deployment_name | Yes | Name of the deployment resource for Azure OpenAI service | `my-gpt4o-deployment` |
# MAGIC
# MAGIC **Note:** Ensure all these parameters are correctly set before running this notebook. You can find most of this information in your Azure portal under your Azure OpenAI resource.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import helper notebook

# COMMAND ----------

# DBTITLE 1,Import Helper Notebook
# MAGIC %run ./helper_external_model

# COMMAND ----------

# MAGIC %md
# MAGIC ## Set up configuration parameters

# COMMAND ----------

# DBTITLE 1,Configurations
dbutils.widgets.text("endpoint_name", "", "Endpoint Name")
dbutils.widgets.text("model_name", "gpt-4o", "Model Name")
dbutils.widgets.text("openai_api_key", "", "Azure OpenAI API Key")
dbutils.widgets.text("openai_api_base", "", "Azure OpenAI API Base URL")
dbutils.widgets.text("openai_api_version", "2024-05-01-preview", "Azure OpenAI API Version")
dbutils.widgets.text("openai_deployment_name", "", "Azure OpenAI Deployment Name")

# COMMAND ----------

# DBTITLE 1,Load Configurations
endpoint_name = dbutils.widgets.get("endpoint_name")
model_name = dbutils.widgets.get("model_name")
openai_api_key = dbutils.widgets.get("openai_api_key")
openai_api_base = dbutils.widgets.get("openai_api_base")
openai_api_version = dbutils.widgets.get("openai_api_version")
openai_deployment_name = dbutils.widgets.get("openai_deployment_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Endpoint Configuration and Creation

# COMMAND ----------

# DBTITLE 1,Prepare Endpoint Configuration
endpoint_config = {
    "served_entities": [
        {
            "name": endpoint_name,
            "external_model": {
                "name": model_name,
                "provider": "openai",
                "task": "llm/v1/chat",
                "openai_config": {
                    "openai_api_type": "azure",
                    "openai_api_key_plaintext": openai_api_key,
                    "openai_api_base": openai_api_base,
                    "openai_api_version": openai_api_version,
                    "openai_deployment_name": openai_deployment_name
                }
            }
        }
    ]
}

# COMMAND ----------

# DBTITLE 1,Create or Update Endpoint
try:
    endpoint_helper = ExternalModelEndpointHelper()
    endpoint = endpoint_helper.create_or_update_endpoint(endpoint_name, endpoint_config)
    print(f"Endpoint '{endpoint_name}' has been successfully created/updated.")
    print("Endpoint details:", endpoint)
except Exception as e:
    print(f"Failed to create or update endpoint: {str(e)}")
