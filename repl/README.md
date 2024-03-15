---
title: "Databricks REPL"
language: python
authors: "Fabian Jakobs, Zac Davies"
date: 2024-03-15

tags: 
 - cli
 - sandbox
---

# Interactively Run Code Against Clusters
Command line tool that opens an interactive REPL against a Databricks cluster.

## Usage
  `repl --lang --cluster-id --profile`

 * `--lang` Language REPL starts as (`r`/`python`/`sql`/`scala`)
 * `--cluster-id` Cluster to attach to
 * `--profile` Profile in `.databrickscfg` to look for credentials
 <!-- * `--multiline` REPL is in multiline mode and needs to `Meta`+`Enter` to submit commands (or `Esc` > `Enter`) -->

Use `repl --help` for more information about a command.
