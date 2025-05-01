# A workspace scanner in preparation to DBFS disablement

This folder contains code that could help with preparing to complete disablement of DBFS.  There are two tools available (each tool has a command-line variant and as notebook with `_nb` suffix):

* `scan_compute.py` (and `scan_compute_nb`) - performs scanning of compute resources (interactive clusters, jobs, DLT pipelines, policies) for use of resources on DBFS (init scripts, libraries, etc.) and output findings.
* `scan_dbfs.py` (and `scan_dbfs_nb`) - performs scanning of DBFS content and trying to classify it and estimate size (Delta tables, Structure Streaming checkpoints, DLT pipelines, ...).  By default it scans the whole DBFS Root (user-accessible part), but you can pass an optional start directory as parameter.

## Usage as command-line utility

1. Install `databricks-sdk` Python package.
1. Setup [environment variables with authentication parameters](https://docs.databricks.com/aws/en/dev-tools/auth/) for a workspace that will be analyzed.
1. Run a specific tool:

   1. `python scan_compute.py` will scan all compute resources and output results to console and also write them into `compute_scan_results.json` file.
   1. `python scan_dbfs.py [start_directory]` will scan DBFS Root (or only a `start_directory` if specified), and output results to console and also write them into `dbfs_scan_results.json` file.

## Usage inside the workspace

1. As **workspace administrator** open the corresponding notebook (`scan_compute_nb` or `scan_dbfs_nb`).
1. Attach to a cluster (i.e. Serverless).
1. Specify parameters in widgets (start directory for `scan_dbfs_nb`, or output directory if you want to persist result to UC Volume (`/Volumes/<catalog>/<schema>/<volume>/`).
1. Press "Run all" and wait for finishing the execution.
1. If output directory is specified, files `compute_scan_results.json` or `dbfs_scan_results.json` will be stored in that directory.

## Scan results

### Format of `compute_scan_results.json`

The `compute_scan_results.json` file contains a JSON object with the following top-level sections:

* `clusters`: Information about interactive clusters, including:
  * Cluster log configurations (`cluster_log_conf`)
  * Init scripts (`init_scripts`)
  * Cluster names (`cluster_name`)

* `cluster_policies`: Information about cluster policies, including:
  * Cluster log configurations (`cluster_log_conf`)
  * Libraries (`libraries`) - JAR/wheel files referenced
  * Policy names (`policy_name`)

* `jobs`: Information about jobs, with each job containing:
  * `tasks`: Individual task configurations including:
    * Python files on DBFS (`python_file_on_dbfs`)
    * Libraries (`libraries`) - JAR/wheel files used
    * Init scripts (`init_scripts`)
  * `job_clusters`: Job-specific cluster configurations including:
    * Cluster log configurations (`cluster_log_conf`)
    * Init scripts (`init_scripts`)
  * Job name (`job_name`)

* `dlt`: Information about Delta Live Tables pipelines, including:
  * Storage location (`storage`)
  * Pipeline name (`name`)
  * Cluster configurations (`clusters`) with:
    * Init scripts (`init_scripts`)

For example:

```json
{
  "clusters": {
    "0313-121649-cxqqcvz0": {
      "cluster_log_conf": "dbfs:/mnt/cluster-logs",
      "cluster_name": "EvHub"
      "libraries": [
        "dbfs:/FileStore/whl/test.whl",
        "dbfs:/FileStore/jars/test.jar"
      ],
    }
  },
  "cluster_policies": {
    "30640179C40010EF": {
      "cluster_log_conf": "dbfs:/mnt/cluster-logs",
      "policy_name": "minimum_global"
    },
    "0005268696213EA3": {
      "libraries": [
        "dbfs:/FileStore/jars/jar-tests-0.0.1.jar"
      ],
      "policy_name": "Test Libraries"
    }
  },
  "jobs": {
    "75390238197996": {
      "tasks": {
        "python_script_on_dbfs": {
          "python_file_on_dbfs": "dbfs:/1.py"
        },
        "abc": {
          "libraries": [
            "dbfs:/1.jar",
            "dbfs:/1.whl"
          ]
        }
      }
    }
  },
  "dlt": {
    "713294fd-9e53-4f2b-b8fe-1d924fb4905c": {
      "libraries": {
        "/Users/user@domain.com/Test/test": {
          "dbfs_file_refs": [
            "dbfs:/FileStore/temp/test_data/input"
          ]
        }
      },
      "storage": "dbfs:/pipelines/713294fd-9e53-4f2b-b8fe-1d924fb4905c",
      "name": "dlt_dabs_pipeline"
    }
  }
}
```

### Format of `dbfs_scan_results.json`

The `dbfs_scan_results.json` file contains a JSON object that maps DBFS paths to information about those paths. Each path entry contains:

* `size`: The total size in bytes of all content under that path
* Optional type classification like `delta_table`, `dlt_storage`, `ss_checkpoint`, `cluster_logs`, etc. if the path contains a specific type of data
* Optional arrays listing specific files:
  * `jar_files`: List of JAR files in that directory
  * `whl_files`: List of Python wheel files in that directory

For example:

```json
{
  "/FileStore/init-scripts": {
      "size": 2406
  },
  "/cluster-logs/1130-094127-3ij40m7s": {
      "type": "cluster_logs",
      "size": 684830
  },
  "/pipelines/28ae6515-b6f4-4e2e-8b65-879009332b7d": {
      "type": "dlt_storage",
      "size": 589529922
  },
  "/tmp": {
    "whl_files": [
        "2.whl",
        "4.whl"
    ],
    "jar_files": [
        "dbutils-in-jar-0.0.1-jar-with-dependencies.jar",
        "kafka-eventhubs-aad-auth-0.0.1-dbr_10.4.jar"
    ],
    "size": 3560732064
  }
}
```

## Known issues

* Scan of DBFS is very slow due to the single-threaded implementation.
* Output file names for results are hardcoded.

## TODOs

* \[ \] Use `blueprints` library for logging
* \[ \] For all compute objects try to find last run/update timestamp...
* \[ \] Parallelize scan of DBFS
* \[ \] Allow to customize output file name in command line utilities
