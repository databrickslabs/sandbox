name := "ServerlessJarJobExample"

// Serverless JAR jobs require Scala 2.13 and JDK 17.
scalaVersion := "2.13.16"
javacOptions ++= Seq("--release", "17")
scalacOptions ++= Seq("-release", "17")

// Spark Connect client version. This tracks the serverless environment version:
// bump the major version only in step with a major environment_version release,
// and the minor/patch version continuously as new client releases ship.
val databricksConnectVersion = "17.3.2"

// Spark Connect client. Provided by the serverless runtime, so it is not
// shipped inside the assembled JAR. The databricks-dbutils-scala SDK (API
// package com.databricks.sdk.scala.dbutils) comes in transitively, so there is
// no need to declare it separately. Add any of your own dependencies here --
// use %% for Scala libraries so sbt resolves the _2.13 artifact.
libraryDependencies += "com.databricks" %% "databricks-connect" % databricksConnectVersion % "provided"

// Fork a JVM on `sbt run` so the javaOptions below are applied.
fork := true
javaOptions += "--add-opens=java.base/java.nio=ALL-UNNAMED"

// Build a deployable fat JAR with `sbt assembly`. No custom assemblyMergeStrategy
// is needed: every heavy dependency is provided by the runtime and marked
// provided, so the assembly contains only this project's own classes.
Compile / mainClass := Some("com.databricks.labs.example.ServerlessJarJobExample")
assembly / assemblyJarName := s"ServerlessJarJobExample-${scalaBinaryVersion.value}-assembly.jar"

// The Scala library is already on the serverless runtime classpath, so there is
// no need to bundle it -- excluding it keeps the assembled JAR small.
assembly / assemblyOption := (assembly / assemblyOption).value.withIncludeScala(false)
