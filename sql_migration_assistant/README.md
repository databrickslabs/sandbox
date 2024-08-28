---
title: Project Legion - SQL Migration Assistant
language: python
author: Robert Whiffin
date: 2024-08-28

tags:
  - SQL
  - Migration
  - copilot
  - GenAi

---

# Project Legion - SQL Migration Assistant

Legion is a Databricks field project to accelerate migrations on to Databricks leveraging the platform’s generative AI
capabilities. It uses an LLM for code conversion and intent summarisation, presented to users in a front end web 
application.

Legion provides a chatbot interface to users for translating input code (for example T-SQL to Databricks SQL) and 
summarising the intent and business purpose of the code. This intent is then embedded for serving in a Vector Search
index for finding similar pieces of code. This presents an opportunity for increased collaboration (find out who is
working on similar projects), rationalisation (identify duplicates based on intent) and discoverability (semantic search).

Legion is a solution accelerator - it is *not* a fully baked solution. This is something for you the customer to take 
on and own. This allows you to present a project to upskill your employees, leverage GenAI for a real use case, 
customise the application to their needs and entirely own the IP.

## Installation


Setting Legion up is a simple and automated process. Ensure you have the [Databricks CLI]
(https://docs.databricks.com/en/dev-tools/cli/index.html) installed and configured with the correct workspace. Install 
the [Databricks Labs Sandbox](https://github.com/databrickslabs/sandbox). Now run the following command in the terminal

```bash 
databricks labs sandbox sql-migration-assistant

# Databricks Infrastructure Requirements

- A no-isolation shared cluster running the ML runtime (tested on DBR 15.0 ML) to run the notebook 2. Gradio app runner
- A vector search endpoint and an embedding model: see docs https://docs.databricks.com/en/generative-ai/vector-search.html#how-to-set-up-vector-search
- Access to a chat LLM (typically one with the name ending **-instruct**). DBRX is recommended based on it's speed of token generation. Use either the foundation model APIs or Provisioned Throughput to serve an LLM.
- A PAT stored in a secret scope
