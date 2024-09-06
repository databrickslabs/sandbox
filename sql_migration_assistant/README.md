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

! [Install video](docs/sql-migration-assistant-set-up.mov)

Setting Legion up is a simple and automated process. Ensure you have the [Databricks CLI]
(https://docs.databricks.com/en/dev-tools/cli/index.html) installed and configured with the correct workspace. Install 
the [Databricks Labs Sandbox](https://github.com/databrickslabs/sandbox). 

First, navigate to where you have installed the Databricks Labs Sandbox. For example
```bash
cd /Documents/sandbox
```

You'll need to install the python requirements in the `requirements.txt` file in the root of the project. 
You may wish to do this in a virtual environment. 
```bash
pip install -r sql-migration-assistant/requirements.txt -q
```
Run the following command to start the installation process, creating all the necessary resources in your workspace.
```bash 
databricks labs sandbox sql-migration-assistant
```

### What Legion needs - during setup above you will create or choose existing resources for the following:

- A no-isolation shared cluster running the ML runtime (tested on DBR 15.0 ML) to host the front end application.
- A catalog and schema in Unity Catalog. 
- A table to store the code intent statements and their embeddings.
- A vector search endpoint and an embedding model: see docs 
https://docs.databricks.com/en/generative-ai/vector-search.html#how-to-set-up-vector-search
- A chat LLM. Pay Per Token is recomended where available, but the set up will also allow for creation of 
a provisioned throughput endpoint.
- A PAT stored in a secret scope chosen by you, under the key `sql-migration-pat`.
