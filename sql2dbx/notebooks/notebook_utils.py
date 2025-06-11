# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook Utilities
# MAGIC This notebook contains utility functions for use in other notebooks.

# COMMAND ----------

# DBTITLE 1,Import Libraries
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyscripts.batch_inference_helper import BatchInferenceResponse
from pyscripts.conversion_result_clean_helper import \
    ConversionResultCleanHelper
from pyspark.sql import DataFrame
from pyspark.sql.functions import coalesce, col, lit, udf, when
from pyspark.sql.types import (ArrayType, FloatType, IntegerType, LongType,
                               StringType, StructField, StructType,
                               TimestampType)

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
                 model_serving_endpoint_for_fix: Optional[str] = None,
                 request_params_for_conversion: Optional[Dict[str, Any]] = None,
                 request_params_for_fix: Optional[Dict[str, Any]] = None):
        """
        Initialize the BatchInferenceResultProcessor with the schema for inference responses and model serving endpoints.

        Args:
            model_serving_endpoint_for_conversion (Optional[str]): The model serving endpoint for conversion.
            model_serving_endpoint_for_fix (Optional[str]): The model serving endpoint for fix.
            request_params_for_conversion (Optional[Dict[str, Any]]): Request parameters for conversion.
            request_params_for_fix (Optional[Dict[str, Any]]): Request parameters for fix.
        """
        self.model_serving_endpoint_for_conversion = model_serving_endpoint_for_conversion
        self.model_serving_endpoint_for_fix = model_serving_endpoint_for_fix

        # Convert request parameters to JSON strings during initialization
        self.request_params_for_conversion_json = json.dumps(
            request_params_for_conversion) if request_params_for_conversion is not None else None
        self.request_params_for_fix_json = json.dumps(
            request_params_for_fix) if request_params_for_fix is not None else None

        self.schema = StructType([
            StructField("input_file_number", LongType(), True),
            StructField("result_content", StringType(), True),
            StructField("result_prompt_tokens", IntegerType(), True),
            StructField("result_completion_tokens", IntegerType(), True),
            StructField("result_total_tokens", IntegerType(), True),
            StructField("result_processing_time_seconds", FloatType(), True),
            StructField("result_timestamp", TimestampType(), True),
            StructField("result_error", StringType(), True),
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
            (
                res.index,
                res.content,
                res.token_usage.prompt_tokens if res.token_usage else None,
                res.token_usage.completion_tokens if res.token_usage else None,
                res.token_usage.total_tokens if res.token_usage else None,
                res.processing_time_seconds,
                current_time,
                res.error,
            )
            for res in responses
        ]
        return spark.createDataFrame(responses_with_timestamp, schema=self.schema)

    def _join_dataframes(self, source_sdf: DataFrame, result_sdf: DataFrame) -> DataFrame:
        """Join the source and result DataFrames."""
        return source_sdf.alias("source").join(result_sdf.alias("result"), on="input_file_number", how="left")

    def _get_update_columns(self) -> List:
        """Get the list of columns to update or add."""
        return [
            # Update conversion target flag based on successful conversion
            when((col("result.result_content").isNotNull()) & (col("result.result_error").isNull()), lit(False))
                .otherwise(col("source.is_conversion_target")).alias("is_conversion_target"),

            # Basic result columns
            coalesce(col("result.result_content"), col("source.result_content")).alias("result_content"),
            coalesce(col("result.result_prompt_tokens"), col("source.result_prompt_tokens")).alias("result_prompt_tokens"),
            coalesce(col("result.result_completion_tokens"), col("source.result_completion_tokens")).alias("result_completion_tokens"),
            coalesce(col("result.result_total_tokens"), col("source.result_total_tokens")).alias("result_total_tokens"),
            coalesce(col("result.result_processing_time_seconds"), col("source.result_processing_time_seconds")).alias("result_processing_time_seconds"),
            coalesce(col("result.result_timestamp"), col("source.result_timestamp")).alias("result_timestamp"),

            # Update result_error with appropriate error handling
            # - Clear error if conversion succeeded (result_content exists and no new error)
            # - Set new error if conversion failed
            # - Keep existing error otherwise
            when((col("result.result_content").isNotNull()) & (col("result.result_error").isNull()), lit(None))
                .when(col("result.result_error").isNotNull(), col("result.result_error"))
                .otherwise(col("source.result_error")).alias("result_error"),

            # Reset analysis-related columns
            lit(None).cast(StringType()).alias("result_python_parse_error"),
            lit(None).cast(ArrayType(StringType())).alias("result_extracted_sqls"),
            lit(None).cast(ArrayType(StringType())).alias("result_sql_parse_errors"),

            # Model serving endpoints and request params
            coalesce(
                lit(self.model_serving_endpoint_for_conversion),
                col("source.model_serving_endpoint_for_conversion")
            ).alias("model_serving_endpoint_for_conversion"),

            coalesce(
                lit(self.model_serving_endpoint_for_fix),
                col("source.model_serving_endpoint_for_fix")
            ).alias("model_serving_endpoint_for_fix"),

            coalesce(
                lit(self.request_params_for_conversion_json),
                col("source.request_params_for_conversion")
            ).alias("request_params_for_conversion"),

            coalesce(
                lit(self.request_params_for_fix_json),
                col("source.request_params_for_fix")
            ).alias("request_params_for_fix"),
        ]

    def _get_select_columns(self, source_sdf: DataFrame, update_columns: List) -> List:
        """Get the list of columns to select in the final DataFrame."""
        excluded_columns = [
            "is_conversion_target",
            "result_content",
            "result_prompt_tokens",
            "result_completion_tokens",
            "result_total_tokens",
            "result_processing_time_seconds",
            "result_timestamp",
            "result_error",
            "result_python_parse_error",
            "result_extracted_sqls",
            "result_sql_parse_errors",
            "model_serving_endpoint_for_conversion",
            "model_serving_endpoint_for_fix",
            "request_params_for_conversion",
            "request_params_for_fix",
        ]
        select_columns = [col("source." + c) for c in source_sdf.columns if c not in excluded_columns]
        select_columns.extend(update_columns)
        return select_columns
