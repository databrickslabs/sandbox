# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook Utilities
# MAGIC This notebook contains utility functions for use in other notebooks.

# COMMAND ----------

# DBTITLE 1,Import Libraries
from datetime import datetime
from typing import List, Optional

from pyspark.sql import DataFrame
from pyspark.sql.functions import coalesce, col, lit, udf, when
from pyspark.sql.types import (ArrayType, IntegerType, LongType, StringType,
                               StructField, StructType, TimestampType)

from scripts.batch_inference_helper import BatchInferenceResponse
from scripts.conversion_result_clean_helper import \
    ConversionResultCleanHelper

# COMMAND ----------

# DBTITLE 1,Define Functions
def clean_conversion_results(target_table: str, size_ratio_threshold: float = 0.9) -> DataFrame:
    """
    Cleans the conversion results in the specified Delta table.

    Args:
        target_table (str): The name of the target table.
        size_ratio_threshold (float): The threshold for the ratio of cleaned content size to original content size. If the ratio is below this threshold, a warning is printed. Default is 0.9 (90%).

    Returns:
        pyspark.sql.DataFrame: The cleaned DataFrame.
    """
    original_df = spark.table(target_table)
    cleaned_df = original_df

    # Apply each UDF function to clean the result_content column
    helper = ConversionResultCleanHelper()
    udf_functions = helper.get_udf_functions()
    for udf_func in udf_functions:
        clean_udf = udf(udf_func, StringType())
        cleaned_df = cleaned_df.withColumn("result_content", clean_udf(cleaned_df["result_content"]))

    # Compare the sizes of the original and cleaned content. If the cleaned content　is under the threshold, print a warning.
    small_content_files_df = compare_content_sizes(original_df, cleaned_df, "result_content", size_ratio_threshold)
    if small_content_files_df.count() > 0:
        print(f"Warning: The following files have cleaned content sizes less than "
              f"{size_ratio_threshold * 100}% of their original sizes, "
              f"indicating potential data loss:")
        display(small_content_files_df)

    # Update result_timestamp if the cleaned content is different from the original content
    return (
        cleaned_df.alias("cleaned")
        .join(original_df.select("input_file_number", "result_content").alias("original"),
              on="input_file_number")
        .withColumn(
            "result_timestamp",
            when(col("cleaned.result_content") != col("original.result_content"), datetime.now())
            .otherwise(col("cleaned.result_timestamp")))
        .drop(col("original.result_content"))
    )


def compare_content_sizes(df1: DataFrame, df2: DataFrame, col_name: str, threshold: float = 0.9) -> DataFrame:
    """
    Compares the sizes of the specified column in two DataFrames and returns a DataFrame
    containing rows where the size ratio is below the threshold.

    Args:
        df1 (DataFrame): The first DataFrame (original).
        df2 (DataFrame): The second DataFrame (cleaned).
        col_name (str): The name of the column to compare sizes.
        threshold (float): The threshold for the size ratio. Default is 0.9 (90%).

    Returns:
        DataFrame: A DataFrame containing rows where the size ratio is below the threshold.
    """
    def safe_len(value):
        if value is None:
            return 0
        return len(value)

    size_udf = udf(safe_len, IntegerType())
    df1 = df1.select(
        "input_file_number",
        "input_file_path",
        size_udf(col(col_name)).alias("original_content_size"))
    df2 = df2.select(
        "input_file_number",
        size_udf(col(col_name)).alias("cleaned_content_size"))
    return (
        df1.join(df2, on="input_file_number")
        .filter(col("cleaned_content_size") / col("original_content_size") < threshold)
        .select(
            "input_file_number",
            "input_file_path",
            "original_content_size",
            "cleaned_content_size",
            (col("cleaned_content_size") / col("original_content_size")).alias("size_ratio"))
    )

class BatchInferenceResultProcessor:
    """
    A class to process batch inference results and merge them with source data in a Databricks environment.
    """

    def __init__(self, model_serving_endpoint_for_conversion: Optional[str] = None,
                 model_serving_endpoint_for_fix: Optional[str] = None):
        """
        Initialize the BatchInferenceResultProcessor with the schema for inference responses and model serving endpoints.

        Args:
            model_serving_endpoint_for_conversion (Optional[str]): The model serving endpoint for conversion.
            model_serving_endpoint_for_fix (Optional[str]): The model serving endpoint for fix.
        """
        self.model_serving_endpoint_for_conversion = model_serving_endpoint_for_conversion
        self.model_serving_endpoint_for_fix = model_serving_endpoint_for_fix
        self.schema = StructType([
            StructField("input_file_number", LongType(), True),
            StructField("result_content", StringType(), True),
            StructField("result_token_count", IntegerType(), True),
            StructField("result_error", StringType(), True),
            StructField("result_timestamp", TimestampType(), True),
        ])

    def process_results(self, source_sdf: DataFrame, responses: List[BatchInferenceResponse]) -> DataFrame:
        """
        Process the batch inference results and merge them with the source DataFrame.

        Args:
            source_sdf (DataFrame): The source DataFrame containing original data.
            responses (List[BatchInferenceResponse]): The list of responses from batch inference.

        Returns:
            DataFrame: The processed DataFrame with merged results.
        """
        result_sdf = self._create_result_dataframe(responses)
        joined_sdf = self._join_dataframes(source_sdf, result_sdf)
        update_columns = self._get_update_columns()
        select_columns = self._get_select_columns(source_sdf, update_columns)

        return joined_sdf.select(*select_columns)

    def _create_result_dataframe(self, responses: List[BatchInferenceResponse]) -> DataFrame:
        """Create a DataFrame from the batch inference responses."""
        current_time = datetime.now()
        responses_with_timestamp = [
            (res.index, res.content, res.token_count, res.error, current_time)
            for res in responses
        ]
        return spark.createDataFrame(responses_with_timestamp, schema=self.schema)

    def _join_dataframes(self, source_sdf: DataFrame, result_sdf: DataFrame) -> DataFrame:
        """Join the source and result DataFrames."""
        return source_sdf.alias("source").join(result_sdf.alias("result"), on="input_file_number", how="left")

    def _get_update_columns(self) -> List:
        """Get the list of columns to update or add."""
        return [
            when((col("result.result_content").isNotNull()) & (col("result.result_error").isNull()), lit(False))
            .otherwise(col("source.is_conversion_target")).alias("is_conversion_target"),
            coalesce(col("result.result_content"), col("source.result_content")).alias("result_content"),
            coalesce(col("result.result_token_count"), col("source.result_token_count")).alias("result_token_count"),
            coalesce(col("result.result_error"), col("source.result_error")).alias("result_error"),
            coalesce(col("result.result_timestamp"), col("source.result_timestamp")).alias("result_timestamp"),
            lit(None).cast(StringType()).alias("result_python_parse_error"),
            lit(None).cast(ArrayType(StringType())).alias("result_extracted_sqls"),
            lit(None).cast(ArrayType(StringType())).alias("result_sql_parse_errors"),
            coalesce(lit(self.model_serving_endpoint_for_conversion), col("source.model_serving_endpoint_for_conversion")).alias("model_serving_endpoint_for_conversion"),
            coalesce(lit(self.model_serving_endpoint_for_fix), col("source.model_serving_endpoint_for_fix")).alias("model_serving_endpoint_for_fix")
        ]

    def _get_select_columns(self, source_sdf: DataFrame, update_columns: List) -> List:
        """Get the list of columns to select in the final DataFrame."""
        excluded_columns = [
            "is_conversion_target",
            "result_content",
            "result_token_count",
            "result_error",
            "result_timestamp",
            "result_python_parse_error",
            "result_extracted_sqls",
            "result_sql_parse_errors",
            "model_serving_endpoint_for_conversion",
            "model_serving_endpoint_for_fix"
        ]
        select_columns = [col("source." + c) for c in source_sdf.columns if c not in excluded_columns]
        select_columns.extend(update_columns)
        return select_columns
