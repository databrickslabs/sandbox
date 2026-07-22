package com.databricks.labs.example

import com.databricks.sdk.scala.dbutils.DBUtils
import org.apache.spark.sql.connect.SparkSession
import org.apache.spark.sql.functions.{col, udf}

import java.util.UUID

/**
 * A minimal, self-contained example of a Scala JAR job that runs on Databricks
 * serverless compute. It demonstrates the three building blocks you are most
 * likely to need:
 *
 *   1. Spark basics    -- get the session, build a DataFrame, read a UC table.
 *   2. UDF basics      -- scalar, map-returning, SQL-registered, and closing
 *                         over a locally-defined class.
 *   3. dbutils basics  -- the notebook/job context and a `dbutils.fs`
 *                         read/write round-trip against a Unity Catalog volume.
 *
 * Serverless JAR jobs run under Spark Connect, so a few things differ from a
 * classic cluster job:
 *
 *   - Get the session with `SparkSession.builder().getOrCreate()`. There is no
 *     `SparkContext` / RDD API (those throw under Spark Connect).
 *   - Build against `databricks-connect` (Spark Connect) and the
 *     `databricks-dbutils-scala` SDK. Both are provided by the runtime, so they
 *     are marked `% provided` in build.sbt and are not shipped in the JAR.
 *   - Target Scala 2.13 and JDK 17 (see build.sbt).
 *
 * Run it with a single argument: the base path of a UC volume you can write to,
 * e.g. `/Volumes/<catalog>/<schema>/<volume>`.
 */
object ServerlessJarJobExample {

  def main(args: Array[String]): Unit = {
    require(
      args.nonEmpty,
      "ServerlessJarJobExample requires a writable UC volume base path as args(0), " +
      "e.g. /Volumes/<catalog>/<schema>/<volume>"
    )
    val volumeBasePath = args(0)

    // Under Spark Connect, getOrCreate() returns the session wired to serverless.
    val spark = SparkSession.builder().getOrCreate()

    // dbutils comes from the databricks-dbutils-scala SDK. Obtain it on the
    // driver and pass it into helpers -- do NOT store it in an object-level val,
    // or its initializer can run inside a UDF closure on an executor and fail.
    val dbutils = DBUtils.getDBUtils()

    sparkBasics(spark)
    udfBasics(spark)
    dbutilsBasics(spark, dbutils, volumeBasePath)

    println("ServerlessJarJobExample: all examples completed successfully")
  }

  // ---------------------------------------------------------------------------
  // 1. Spark basics
  // ---------------------------------------------------------------------------

  def sparkBasics(spark: SparkSession): Unit = {
    println(s"Spark version: ${spark.version}")

    // Build a DataFrame and collect a few rows.
    val ids = spark.range(10).limit(3).collect().toSeq
    println(s"spark.range(10).limit(3) = ${ids.mkString(", ")}")

    // Read a Unity Catalog table. `samples` is a built-in public catalog
    // available on Databricks workspaces, so this needs no setup.
    val rows = spark.read.table("samples.nyctaxi.trips").limit(10).count()
    println(s"Read $rows rows from samples.nyctaxi.trips")
  }

  // ---------------------------------------------------------------------------
  // 2. UDF basics
  // ---------------------------------------------------------------------------

  def udfBasics(spark: SparkSession): Unit = {
    import spark.implicits._

    // A scalar UDF returning a String.
    val greet = udf((v: Int) => s"hello world $v")
    val greeted = spark.range(3).select(greet(col("id")).as("v")).as[String].collect().toSeq
    println(s"scalar UDF: ${greeted.mkString(", ")}")

    // A UDF returning a Map.
    val toMap = udf((v: Int) => Map(v -> "some value"))
    val mapped =
      spark.range(1).select(toMap(col("id")).as("m")).as[Map[Int, String]].collect().toSeq
    println(s"map UDF: ${mapped.mkString(", ")}")

    // Register a UDF for use from SQL.
    spark.udf.register("greet", greet)
    val fromSql = spark.sql("SELECT greet(1) AS v").as[String].collect().head
    println(s"SQL-registered UDF: $fromSql")

    // A UDF closing over a locally-defined class. Spark ships the closure (and
    // the class) to the executors, so this exercises closure serialization.
    val withClass = udf((x: Int) => new Multiplier(x).result)
    val computed = spark.range(5).select(withClass(col("id"))).as[Int].collect().sorted.toSeq
    println(s"UDF with local class: ${computed.mkString(", ")}")
  }

  /** A small class captured by a UDF closure and shipped to the executors. */
  private class Multiplier(x: Int) {
    def result: Int = x * 42 + 5
  }

  // ---------------------------------------------------------------------------
  // 3. dbutils basics
  // ---------------------------------------------------------------------------

  def dbutilsBasics(spark: SparkSession, dbutils: DBUtils, volumeBasePath: String): Unit = {
    import spark.implicits._

    // The job/notebook context carries tags such as the job and run identifiers.
    println(s"notebook context tags: ${dbutils.notebook.getContext().tags}")

    // A Spark read/write round-trip against a UC volume, cleaned up with
    // dbutils.fs.rm afterwards.
    val path = s"$volumeBasePath/example_${UUID.randomUUID().toString}"
    try {
      Seq("hello world").toDF("value").write.mode("overwrite").text(path)
      val readBack = spark.read.text(path).as[String].collect().toSeq
      require(readBack == Seq("hello world"), s"volume round-trip mismatch, got $readBack")
      println(s"dbutils.fs volume round-trip OK at $path")
    } finally {
      // Best-effort cleanup.
      try dbutils.fs.rm(path, true)
      catch { case _: Throwable => () }
    }
  }
}
