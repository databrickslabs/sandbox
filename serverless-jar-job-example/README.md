---
title: "Serverless Scala JAR job example"
language: scala
author: "Imran Hasan"
date: 2026-07-22

tags:
- scala
- spark-connect
- serverless
- jar
- jobs
- dbutils
---

# Serverless Scala JAR job example

A minimal, self-contained Scala JAR job that runs on **Databricks serverless
compute**, packaged as a **Databricks Asset Bundle**. It is meant as a
copy-and-go starting point: the bundle builds the JAR with `sbt assembly`,
uploads it, and defines a serverless JAR job. The code demonstrates three basic
building blocks:

1. **Spark basics** — get the session, build a DataFrame, read a Unity Catalog table.
2. **UDF basics** — scalar, map-returning, SQL-registered, and a UDF closing over a locally-defined class.
3. **dbutils basics** — the job/notebook context and a `dbutils.fs` read/write round-trip against a UC volume.

## Serverless specifics

Serverless JAR jobs run under **Spark Connect**, which differs from a classic
cluster job in a few ways this example follows:

- Get the session with `SparkSession.builder().getOrCreate()`. There is **no**
  `SparkContext` / RDD API — those throw under Spark Connect.
- Build against the **Spark Connect** client (`databricks-connect`) and the
  **`databricks-dbutils-scala`** SDK (package `com.databricks.sdk.scala.dbutils`).
  Both are provided by the runtime, so they are marked `% provided` and are not
  shipped inside your JAR.
- Target **Scala 2.13** and **JDK 17**.

## Layout

```
serverless-jar-job-example/
├── databricks.yml             # bundle: build the JAR, define variables and target
├── resources/
│   └── serverless-jar-job-example.job.yml   # the serverless JAR job
├── build.sbt                  # Scala 2.13.16, JDK 17, provided deps, assembly config
├── project/
│   ├── plugins.sbt            # sbt-assembly plugin
│   └── build.properties       # sbt version
└── src/main/scala/com/databricks/labs/example/
    └── ServerlessJarJobExample.scala
```

## Prerequisites

- The [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html),
  authenticated to your workspace.
- [sbt](https://www.scala-sbt.org/) and JDK 17 (the bundle invokes `sbt assembly`).

## Configure

Edit `databricks.yml`:

- Set the `dev` target's `workspace.host` to your workspace URL.
- Set the `volume_base` variable default to a Unity Catalog volume you can write
  to, e.g. `/Volumes/<catalog>/<schema>/<volume>` (or pass it at deploy time with
  `--var volume_base=...`).

## Deploy and run

The bundle builds the JAR, uploads it, and creates the job in one step:

```bash
databricks bundle deploy -t dev
databricks bundle run -t dev serverless-jar-job-example
```

`bundle deploy` runs `sbt assembly` to produce the fat JAR at
`target/scala-2.13/ServerlessJarJobExample-2.13-assembly.jar`, uploads it to the
workspace artifact path, and registers the serverless JAR job. On success the
run's driver log ends with:

```
ServerlessJarJobExample: all examples completed successfully
```

The job's single argument (`args(0)`) is the `volume_base` variable — a UC volume
the job can write to; the `dbutils.fs` example writes a temporary file there and
cleans it up afterwards.

## References

- [Create and run JARs on serverless compute](https://docs.databricks.com/aws/en/jobs/how-to/use-jars-in-workflows)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
