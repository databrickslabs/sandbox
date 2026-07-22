name := "ServerlessJarJobExample"

// Serverless JAR jobs require Scala 2.13 and JDK 17.
scalaVersion := "2.13.16"
javacOptions ++= Seq("--release", "17")
scalacOptions ++= Seq("-release", "17")

// Spark Connect client. Provided by the serverless runtime, so it is not
// shipped inside the assembled JAR.
libraryDependencies += "com.databricks" %% "databricks-connect" % "17.3.2" % "provided"

// dbutils for Scala. Use the databricks-dbutils-scala SDK (API package
// com.databricks.sdk.scala.dbutils); it is in the serverless provided-library
// list, so it is marked provided as well. Add any of your own dependencies
// here -- use %% for Scala libraries so sbt resolves the _2.13 artifact.
libraryDependencies += "com.databricks" %% "databricks-dbutils-scala" % "0.1.4" % "provided"

// Fork a JVM on `sbt run` so the javaOptions below are applied.
fork := true
javaOptions += "--add-opens=java.base/java.nio=ALL-UNNAMED"

// Build a deployable fat JAR with `sbt assembly`. No custom assemblyMergeStrategy
// is needed: every heavy dependency is provided by the runtime and marked
// provided, so the assembly contains only this project's own classes.
Compile / mainClass := Some("com.databricks.labs.example.ServerlessJarJobExample")
assembly / assemblyJarName := s"ServerlessJarJobExample-${scalaBinaryVersion.value}-assembly.jar"
