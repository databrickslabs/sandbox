## Generates UML diagram for specified Spark databases

Generates [PlantUML](https://plantuml.com/) diagram for all, or selected databases registered in Databricks/Spark.  Generated UML diagram then could be converted into PDF/SVG/PNG or other formats using `plantuml` command-line tool.

There are two variants of the code:
1. [database-diagram-builder-notebook.py](database-diagram-builder-notebook.py) - Databricks notebook that accepts parameters via widgets, and besides generation of PlantUML source code, can also generate PDF/SVG/PNG representation.
1. [database-diagram-builder-standalone.py](database-diagram-builder-standalone.py) - for use with Databricks connect or OSS Spark.  Only generates PlantUML source code.
