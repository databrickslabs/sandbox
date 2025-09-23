---
title: "Managed File Push"
language: python
author: "Chi Yang"
date: 2025-08-07

tags: 
- ingestion
- file
- nocode
---

# Managed File Push
## Table of Contents
- [Quick Start](#quick-start)
- [Debug Table Issues](#debug-table-issues)

## Quick Start
### Step 1. Configure tables
Define the catalog and a NEW schema name where the tables will land in `./dab/databricks.yml`
```
variables:
  catalog_name:
    description: The existing catalog where the NEW schema will be created.
    default: main
  schema_name:
    description: The name of the NEW schema where the tables will be created.
    default: filepushschema

```
Edit the table configs in `./dab/src/configs/tables.json`. Only `name` and `format` are required for a table.

For possible `format_options` checkout [Auto Loader Options article](https://docs.databricks.com/aws/en/ingestion/cloud-object-storage/auto-loader/options). Not all options are supported. If you are not sure, feel free to specify only the `name` and `format`, or follow steps in [Debug Table Issues](#debug-table-issues) section to help come up with the proper options.
```
[
  {
    "name": "table1",
    "format": "csv",
    "format_options": {
      "escape": "\""
    },
    "schema_hints": "id int, name string"
  },
  {
    "name": "table2",
    "format": "json"
  }
  ,
  ...
]

```

### Step 2. Deploy & setup
```
$ cd dab
$ databricks bundle deploy
$ databricks bundle run configuration_job
```
Wait for the configuration job to finish before moving to the next step.

### Step 3. Retrieve endpoint & push files
Get the volume path for uploading the files
```
$ databricks tables get main.filepushschema.table1 --output json | jq '.properties["filepush.table_volume_path_data"]'
```
Example output:
```
"/Volumes/main/filepushschema/main_filepushschema_filepush_volume/data/table1"
```
Upload files to the path above using the [UC Volume APIs of your choice](https://docs.databricks.com/aws/en/volumes/volume-files#methods-for-managing-files-in-volumes). Here is an example using the **REST API**:
```
$ curl --request PUT https://<workspace-url>/api/2.0/fs/files/Volumes/main/filepushschema/main_filepushschema_filepush_volume/data/table1/datafile1.csv" \
    --header "Authorization: Bearer <PAT>" \
    --header "Content-Type: application/octet-stream \
    --data-binary "@/local/file/path/datafile1.csv"
```
Here is another example using the **Databricks CLI**. This way you do not need to specify the file name at destination. Pay attention to the `dbfs:` URL scheme for the destination path:
```
$ databricks fs cp /local/file/path/datafile1.csv dbfs:/Volumes/main/filepushschema/main_filepushschema_filepush_volume/data/table1
```

After maximum 1 minute, the data should land the corresponding table e.g. `main.filepushschema.table1`

## Debug Table Issues
In case the data is not parsed correctly in the destination table, follow the steps below to fix the table configs.
### Step 1. Configure tables to debug
Configure tables just like [Step 1 in Quick Start](#step-1-configure-tables).

### Step 2. Deploy & Setup in ***dev mode***
```
$ cd dab
$ databricks bundle deploy -t dev
$ databricks bundle run configuration_job -t dev
```
Wait for the configuration job to finish before moving to the next step. Example output:
```
2025-09-23 22:03:04,938 [INFO] initialization - ==========
catalog_name: main
schema_name: dev_chi_yang_filepushschema
volume_path_root: /Volumes/main/dev_chi_yang_filepushschema/main_filepushschema_filepush_volume
volume_path_data: /Volumes/main/dev_chi_yang_filepushschema/main_filepushschema_filepush_volume/data
volume_path_archive: /Volumes/main/dev_chi_yang_filepushschema/main_filepushschema_filepush_volume/archive
==========
```
Pay attention that, ***dev mode put a prefix to the schema name***, and you should use the name output by the initialization job for the remaining steps.

### Step 3. Retrieve endpoint & push files to debug
Get the volume path for uploading the files, pay attention to the ***prefix*** name of the schema:
```
$ databricks tables get main.dev_chi_yang_filepushschema.table1 --output json | jq '.properties["filepush.table_volume_path_data"]'
```
Example output:
```
"/Volumes/main/dev_chi_yang_filepushschema/main_filepushschema_filepush_volume/data/table1"
```
Follow the remaining steps of [Step 3 in Quick Start](#step-3-retrieve-endpoint--push-files) to push files for debug.

### Step 4. Debug table configs
Open the `refresh_pipeline` in the workspace:
```
$ databricks bundle open refresh_pipeline -t dev
```
Then click `Edit pipeline` to launch the development UI. Open the notebook `debug_table_config` and follow the instruction there to fix the table configs. Remember to copy over the config to the table configs in `./dab/src/configs/tables.json`.

### Step 5. Fix the table configs in production
Go though [Step 2 in Quick Start](#step-2-deploy--setup) to deploy the updated config, then issue a full-refresh to fix the problematic data in the table:
```
$ databricks bundle run refresh_pipeline --full-refresh table1
```
