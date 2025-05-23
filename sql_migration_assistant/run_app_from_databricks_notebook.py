# Databricks notebook source
# MAGIC %md
# MAGIC # This notebook is automatically created during setup of the SQL Migration Assistant.
# MAGIC
# MAGIC To run the lauch the migration assistant review app, make sure the notebook is attached to classic (non-serverless compute, DBR >= 15.1) and press run all. The link for the review app will be presented below.
# MAGIC
# MAGIC If you want to share the app with users outside of Databricks, for example so non technical SMEs can contribute to LLM prompt development, the notebook needs to run on a no isolation shared cluster.

# COMMAND ----------
pip install databricks-sdk -U -q

# COMMAND ----------
pip install gradio==4.27.0 pyyaml aiohttp==3.10.5 databricks-labs-blueprint==0.8.2 databricks-labs-lsql==0.9.0 -q

# COMMAND ----------
pip install fastapi==0.112.2 pydantic==2.8.2 dbtunnel==0.14.6 openai -q

# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------
from utils.runindatabricks import run_app
run_app()