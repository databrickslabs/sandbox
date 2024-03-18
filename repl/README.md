---
title: "Databricks REPL"
language: python
authors: "Fabian Jakobs, Zac Davies"
date: 2024-03-15

tags: 
 - cli
 - sandbox
---

# Databricks REPL
Interactive shell to run all code against Databricks clusters in any of the Databricks supported languages.

## Features

* Attached to serverless when available if no other cluster specified
* Dynamically switch languages
* Rich formatting for code and outputs
* Leverages existing Databricks CLI & SDK constructs (Auth etc.)
* Benefits directly from capability of connected cluster (e.g. Unity Catalog)

## Quick Start

```sh
# install from sandbox repl branch
databricks labs install sandbox@repl
# ensure ~.databrickscfg is configured
databricks labs sandbox repl
```

## Usage
  `repl --lang --cluster-id <id> --profile <profile>`

 * `--lang` Language REPL starts as (`r`/`python`/`sql`/`scala`)
 * `--cluster-id` Cluster to attach to
 * `--profile` Profile in `.databrickscfg` to look for credentials
 <!-- * `--multiline` REPL is in multiline mode and needs to `Meta`+`Enter` to submit commands (or `Esc` > `Enter`) -->

Use `repl --help` for more information about a command.
