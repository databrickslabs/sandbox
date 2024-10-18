# Databricks notebook source
# MAGIC %md
# MAGIC # External Model - Amazon Bedrock Setup
# MAGIC This notebook sets up an external model endpoint for Amazon Bedrock in Databricks.
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Ensure that you have access to the desired models in Amazon Bedrock. For information on managing model access, refer to the [Amazon Bedrock Model Access documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).
# MAGIC - Your AWS IAM user or role must have the necessary permissions to invoke Bedrock models, including the `bedrock:InvokeModel` action on Bedrock resources.
# MAGIC - You have set up the AWS credentials (Access Key ID and Secret Access Key) with the required permissions.
# MAGIC - You have the following information available:
# MAGIC   - Your AWS Access Key ID and Secret Access Key
# MAGIC   - The AWS region where your Bedrock models are deployed
# MAGIC   - The name of the Bedrock model you want to use
# MAGIC
# MAGIC ## Parameters
# MAGIC | Parameter Name | Required | Description | Example |
# MAGIC |----------------|----------|-------------|---------|
# MAGIC | endpoint_name | Yes | Name for the new Databricks serving endpoint | `my-bedrock-endpoint` |
# MAGIC | model_name | Yes | Name of the external model | `claude-3-5-sonnet-20240620-v1:0` |
# MAGIC | region | Yes | Region where the external model is deployed | `us-east-1` |
# MAGIC | aws_access_key_id | Yes | AWS Access Key ID for Amazon Bedrock authentication | ***your-access-key-id*** |
# MAGIC | aws_secret_access_key | Yes | AWS Secret Access Key for Amazon Bedrock authentication | ***your-secret-access-key*** |
# MAGIC
# MAGIC **Note:** Ensure all these parameters are correctly set before running this notebook. You can find most of this information in your AWS Management Console or from your AWS administrator.

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
dbutils.widgets.text("model_name", "claude-3-5-sonnet-20240620-v1:0", "Model Name")
dbutils.widgets.text("region", "us-east-1", "AWS Region")
dbutils.widgets.text("aws_access_key_id", "", "AWS Access Key ID")
dbutils.widgets.text("aws_secret_access_key", "", "AWS Secret Access Key")

# COMMAND ----------

# DBTITLE 1,Load Configurations
endpoint_name = dbutils.widgets.get("endpoint_name")
model_name = dbutils.widgets.get("model_name")
region = dbutils.widgets.get("region")
aws_access_key_id = dbutils.widgets.get("aws_access_key_id")
aws_secret_access_key = dbutils.widgets.get("aws_secret_access_key")

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
                "provider": "amazon-bedrock",
                "task": "llm/v1/chat",
                "amazon_bedrock_config": {
                    "aws_region": region,
                    "aws_access_key_id_plaintext": aws_access_key_id,
                    "aws_secret_access_key_plaintext": aws_secret_access_key,
                    "bedrock_provider": "anthropic",
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
