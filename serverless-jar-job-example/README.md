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
compute**. It is meant as a copy-and-go starting point: it builds into a single
fat JAR with `sbt assembly` and demonstrates three basic building blocks:

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
├── build.sbt                  # Scala 2.13.16, JDK 17, provided deps, assembly config
├── project/
│   ├── plugins.sbt            # sbt-assembly plugin
│   └── build.properties       # sbt version
└── src/main/scala/com/databricks/labs/example/
    └── ServerlessJarJobExample.scala
```

## Build

You need [sbt](https://www.scala-sbt.org/) and JDK 17.

```bash
sbt clean assembly
```

This produces the fat JAR at:

```
target/scala-2.13/ServerlessJarJobExample-2.13-assembly.jar
```

## Deploy and run

1. Create a job with a **JAR task** on **serverless** compute:
   - Main class: `com.databricks.labs.example.ServerlessJarJobExample`
   - Environment JAR dependency: the uploaded JAR (drag and drop it into the file selector, or browse to select it from a Unity Catalog volume or workspace location)
   - Parameter (`args(0)`): a writable UC volume base path,
     e.g. `/Volumes/<catalog>/<schema>/<volume>`

2. Run the job. On success the driver log ends with:

   ```
   ServerlessJarJobExample: all examples completed successfully
   ```

The single argument is the base path of a UC volume the job can write to; the
`dbutils.fs` example writes a temporary file there and cleans it up afterwards.

## References

- [Create and run JARs on serverless compute](https://docs.databricks.com/aws/en/jobs/how-to/use-jars-in-workflows)
