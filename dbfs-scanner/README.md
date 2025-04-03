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


## Known issues

* Scan of DBFS is very slow due to the single-threaded implementation.
* Output file names for results are hardcoded.


## TODOs

* \[ \] Use `blueprints` library for logging
* \[ \] For all compute objects try to find last run/update timestamp...
* \[ \] Parallelize scan of DBFS
* \[ \] Allow to customize output file name in command line utilities
