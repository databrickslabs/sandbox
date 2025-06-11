---
title: "sql2dbx"
language: python
author: "Hiroyuki Nakazato"
date: 2025-4-25

tags:
- sql-migration-tool
- multi-dialect-sql
- llm
- automation
---

# sql2dbx
**sql2dbx** is an automation tool designed to convert SQL files into Databricks notebooks. It leverages Large Language Models (LLMs) to perform the conversion based on system prompts tailored for various SQL dialects. sql2dbx consists of a series of Databricks notebooks.

## How to Execute
1. Clone the [databrickslabs/sandbox](https://github.com/databrickslabs/sandbox) repository.
2. Import the `sql2dbx` folder into your Databricks workspace.
3. Run either notebook as your entry point:
   - `notebooks/00_main` (English)
   - `notebooks/00_main_ja` (Japanese)

These notebooks contain all instructions and documentation needed to use sql2dbx.
