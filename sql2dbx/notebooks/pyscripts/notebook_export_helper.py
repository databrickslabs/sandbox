import base64
import os
from dataclasses import dataclass
from typing import List, Optional

from .notebook_i18n import MessageKey, get_language_messages


@dataclass
class ExportInput:
    """
    Input data for exporting a script to a Databricks notebook.

    Attributes:
        input_file_path (str): Path to the source script file
        output_dir (str): Directory where the notebook will be saved
        code (str): Content of the script to be converted
        comment_lang (str): Language code for comments (e.g., "English", "Japanese")
        python_parse_error (str, optional): Python syntax error message, if any
        sql_parse_error (List[str], optional): List of SQL syntax error messages, if any
    """
    input_file_path: str
    output_dir: str
    code: str
    comment_lang: str
    python_parse_error: str = None
    sql_parse_error: List[str] = None


@dataclass
class ExportOutput:
    """
    Output data from exporting a script to a Databricks notebook.

    Attributes:
        input_file_path (str): Original input file path
        output_file_path (str): Path where the notebook was saved
        base64_encoded_content (str): Base64 encoded notebook content
        base64_encoded_content_size (int): Size of the encoded content
        export_succeeded (bool): Whether the export succeeded
        export_error (str, optional): Error message if export failed
        parse_error_count (int): Number of parse errors found
    """
    input_file_path: str
    output_file_path: str
    base64_encoded_content: str
    base64_encoded_content_size: int
    export_succeeded: bool = False
    export_error: Optional[str] = None
    parse_error_count: int = 0


class NotebookExportHelper:
    """
    Helper class for exporting scripts to Databricks notebooks.

    This class handles the conversion of script files to Databricks notebook format,
    including internationalization support and error reporting.
    """

    def process_notebooks(self, exporter_inputs: List[ExportInput]) -> List[ExportOutput]:
        """
        Processes a list of ExportInput objects, generates Databricks notebook content,
        and returns a list of ExportOutput objects containing the output file paths
        and their base64 encoded content.

        Args:
            exporter_inputs (List[ExportInput]): List of input objects with script details

        Returns:
            List[ExportOutput]: List of output objects with notebook details
        """
        results = []
        unique_paths = self.generate_unique_output_paths(exporter_inputs)

        for exporter_input, output_file_path in zip(exporter_inputs, unique_paths):
            # Skip if code is None or empty
            if not exporter_input.code:
                print(f"Skipping file due to empty code: {exporter_input.input_file_path}")
                continue

            # Create Databricks notebook content and encode with base64
            notebook_content = self.create_notebook_content(output_file_path=output_file_path, ex_in=exporter_input)
            encoded_content = base64.b64encode(notebook_content.encode('utf-8')).decode('utf-8')

            # Calculate parse error count
            parse_error_count = (1 if exporter_input.python_parse_error else 0) + \
                (len(exporter_input.sql_parse_error) if exporter_input.sql_parse_error else 0)

            # Append ExportOutput object to the results list
            results.append(ExportOutput(
                input_file_path=exporter_input.input_file_path,
                output_file_path=output_file_path,
                base64_encoded_content=encoded_content,
                base64_encoded_content_size=len(encoded_content),
                parse_error_count=parse_error_count,
                export_succeeded=True  # Set to True as we've successfully created the content
            ))

        return results

    def create_notebook_content(self, output_file_path: str, ex_in: ExportInput) -> str:
        """
        Creates the content for a Databricks notebook.

        This function generates the notebook content including:
        - A header with the notebook name and source script information
        - The original code from the input script
        - Any Python or SQL syntax errors, if present
        - A message indicating no errors if both Python and SQL parse errors are absent

        Args:
            output_file_path (str): The path where the notebook will be saved
            ex_in (ExportInput): An object containing the input script details and any syntax errors

        Returns:
            str: The complete content of the Databricks notebook
        """
        notebook_name = os.path.basename(output_file_path)
        messages = get_language_messages(ex_in.comment_lang)
        notebook_content = (
            f"# Databricks notebook source\n"
            f"# MAGIC %md\n"
            f"# MAGIC # {notebook_name}\n"
            f"# MAGIC {messages[MessageKey.NOTEBOOK_DESCRIPTION]}\n"
            f"# MAGIC \n"
            f"# MAGIC {messages[MessageKey.SOURCE_SCRIPT]}: `{ex_in.input_file_path}`\n"
            f"# COMMAND ----------\n"
            f"{ex_in.code}\n"
            f"# COMMAND ----------\n"
            f"# MAGIC %md\n"
            f"# MAGIC ## {messages[MessageKey.SYNTAX_CHECK_RESULTS]}\n"
        )
        if ex_in.python_parse_error or ex_in.sql_parse_error:
            notebook_content += (
                f"# MAGIC {messages[MessageKey.ERRORS_FROM_CHECKS]}\n"
            )
            if ex_in.python_parse_error:
                notebook_content += (
                    f"# MAGIC ### {messages[MessageKey.PYTHON_SYNTAX_ERRORS]}\n"
                    f"# MAGIC ```\n"
                    f"# MAGIC {ex_in.python_parse_error}\n"
                    f"# MAGIC ```\n"
                )
            if ex_in.sql_parse_error:
                notebook_content += (
                    f"# MAGIC ### {messages[MessageKey.SPARK_SQL_SYNTAX_ERRORS]}\n"
                    f"# MAGIC ```\n"
                )
                for error in ex_in.sql_parse_error:
                    notebook_content += f"# MAGIC {error}\n"
                notebook_content += f"# MAGIC ```\n"
        else:
            notebook_content += (
                f"# MAGIC {messages[MessageKey.NO_ERRORS_DETECTED]}\n"
                f"# MAGIC {messages[MessageKey.REVIEW_CODE]}\n"
            )
        return notebook_content

    def generate_unique_output_paths(self, exporter_inputs: List[ExportInput]) -> List[str]:
        """
        Generates unique output file paths by appending a number if the file already exists.
        The number is incremented from 1 until a unique path is found.

        Args:
            exporter_inputs (List[ExportInput]): List of export input objects

        Returns:
            List[str]: List of unique output file paths
        """
        seen_paths = set()
        unique_paths = []

        for ex_in in exporter_inputs:
            base_name = os.path.basename(ex_in.input_file_path)
            name, _ = os.path.splitext(base_name)
            output_file_path = os.path.join(ex_in.output_dir, name)
            counter = 1

            while output_file_path in seen_paths:
                output_file_path = os.path.join(ex_in.output_dir, f"{name}_{counter}")
                counter += 1

            seen_paths.add(output_file_path)
            unique_paths.append(output_file_path)

        return unique_paths
