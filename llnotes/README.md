---
title: "Generate GitHub release notes with LLMs hosted on Databricks Model Serving"
language: go
author: "Serge Smertin"
date: 2024-01-06

tags: 
 - cli
 - sandbox
---

Generate GitHub release notes with LLMs hosted on Databricks Model Serving
---

The code provided is a Go program that uses the Databricks SDK and the lite library to create a release notes assistant called "llnotes". The main function initializes the program with necessary configurations and runs the lite framework along with several commands including `pull-request`, `upcoming-release`, `diff`, and `announce`. The `pull-request` command generates a pull request description, while the `upcoming-release` command generates release notes for the upcoming release. The `diff` command generates release notes between two git references, and the `announce` command generates a release announcement that can be edited using a chat model. The program accepts various flags and configurations for GitHub and Databricks integration.

To authenticate with Databricks, run `databricks auth login https://....azuredatabricks.net/` or `databricks auth login https://....cloud.databricks.com/`. To authenticate with GitHub, run `gh auth login`.