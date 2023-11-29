---
title: "Databricks Sandboxes metadata magagement"
language: go
author: "Serge Smertin"
date: 2023-11-29

tags: 
 - cli
 - sandbox
---

# Updates metadata about Databricks Sandbox repositories

Synchronise metadata across sandbox repositories

## Usage
  `metascan [command]``

## Available Commands
  * `scan` Scans frontmatter of README.md files in current directory and shows summary

## Flags

 * `--debug` Enable debug log output

Use "metascan [command] --help" for more information about a command.

# `metascan scan-thos`

Scans frontmatter of README.md files in current directory and shows summary

Flags:

 * ` --fail`   fail on validation errors

Sample output:

```
Name                      Title                                              Author         Updated
metascan                  Databricks Sandboxes metadata magagement           Serge Smertin  2023-11-29
runtime-packages          Databricks Runtime package discovery               Serge Smertin  2023-11-29
go-libs                   Utility libraries for Go                           Serge Smertin  2023-11-29
ip_access_list_analyzer   Analyzer/fix tool for Databricks IP Access Lists   Alex Ott       2023-11-29
database-diagram-builder  UML diagram builder for specified Spark Databases  Alex Ott       2023-11-29
```