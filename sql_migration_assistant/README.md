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

## Installation Videos


https://github.com/user-attachments/assets/e665bcf4-265f-4a47-81eb-60845a72c798

https://github.com/user-attachments/assets/fa622f96-a78c-40b8-9eb9-f6671c4d7b47

https://github.com/user-attachments/assets/1a58a1b5-2dcf-4624-b93f-214735162584

When the installation completes a link to the app will be displayed in the terminal. Copy and paste this into your 
browser to access the app. The app is running on a single node cluster which will be terminated after 2 hours of
inactivitiy.


Setting Legion up is a simple and automated process. Ensure you have the [Databricks CLI]
(https://docs.databricks.com/en/dev-tools/cli/index.html) installed and configured with the correct workspace.

Once the Databricks CLI has been installed and configured, run the following command to install the Databricks Labs 
Sandbox and the SQL Migration Assistant.

NB - the Sandbox repo has a different release frequency to Legion. To get the latest version of Legion, 
install from the main branch as per the command below.

```bash
databricks labs install sandbox@main && databricks labs sandbox sql-migration-assistant
```

### What Legion needs - during setup above you will create or choose existing resources for the following:

- A no-isolation shared cluster to host the front end application.
- A catalog and schema in Unity Catalog. 
- A table to store the code intent statements and their embeddings.
- A vector search endpoint and an embedding model: see docs 
https://docs.databricks.com/en/generative-ai/vector-search.html#how-to-set-up-vector-search
- A chat LLM. [Databricks Pay Per Token models](https://docs.databricks.com/en/machine-learning/foundation-models/supported-models.html)
are recomended for the initial evaluation, but token limits will impede ability for handling long inputs. Instead choose 
a [Provisioned Throughput model](https://docs.databricks.com/en/machine-learning/foundation-models/deploy-prov-throughput-foundation-model-apis.html)
or an [External Model](https://docs.databricks.com/en/generative-ai/external-models/index.html)
- A PAT stored in a secret scope chosen by you, under the key `sql-migration-pat`.


### Restarting the application
During installation a set of artefacts are created in your User folder in the Databricks workspace, in the 
subfolder *.sql-migration-assistant*. To restart the application, attach the notebook 
**run_app_from_databricks_notebook** (in the top level of this folder) to a 
[Dedicated (aka Single User) Access Mode](https://docs.databricks.com/en/compute/configure.html#access-mode) cluster and 
click Run All in the toolbar on the top. 

### Expanding access to the UI
The installation process will create an app accessible only to the user who installed it. Expanding access to the app
requires updating the owner of the app from the user who created it to the group who will use it. 
[This page](https://docs.databricks.com/en/admin/users-groups/groups.html) details group management in Databricks if
you need to create a new group for this. The following changes must be made to grant access to the app to a group:
- The serving cluster must be changed to run as a group. This is a preview feature and must be enabled via the [Previews
UI](https://docs.databricks.com/en/admin/workspace-settings/manage-previews.html). Please reach out to your account team
if you encounter difficulties. 
- During installation the schema sql-migration-assistant was created in a catalog you choose. This schema must be shared
with the group. The group will at minimum need USE SCHEMA, READ VOLUME, EXECUTE, SELECT, MODIFY and WRITE VOLUME 
permissions. For ease it is recommended to grant the group ALL PRIVILEGES on the schema.  
- Grant the group permission to run the notebook **run_app_from_databricks_notebook** in the folder 
*.sql-migration-assistant* in the Users folder of the user who initially installed the app.