import base64
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExportInput:
    input_file_path: str
    output_dir: str
    code: str
    python_parse_error: str = None
    sql_parse_error: List[str] = None


@dataclass
class ExportOutput:
    output_file_path: str
    base64_encoded_content: str
    base64_encoded_content_size: int
    export_succeeded: bool = False
    export_error: Optional[str] = None
    parse_error_count: int = 0


class NotebookExportHelper:
    def process_notebooks(self, exporter_inputs: List[ExportInput]) -> List[ExportOutput]:
        """
        Processes a list of ExportInput objects, generates Databricks notebook content,
        and returns a list of ExportOutput objects containing the output file paths 
        and their base64 encoded content.
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
                output_file_path=output_file_path,
                base64_encoded_content=encoded_content,
                base64_encoded_content_size=len(encoded_content),
                parse_error_count=parse_error_count
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
        notebook_content = (
            f"# Databricks notebook source\n"
            f"# MAGIC %md\n"
            f"# MAGIC # {notebook_name}\n"
            f"# MAGIC This notebook was automatically converted from the script below. "
            f"It may contain errors, so use it as a starting point and make necessary corrections.\n"
            f"# MAGIC \n"
            f"# MAGIC Source script: `{ex_in.input_file_path}`\n"
            f"# COMMAND ----------\n"
            f"{ex_in.code}\n"
            f"# COMMAND ----------\n"
            f"# MAGIC %md\n"
            f"# MAGIC ## Static Syntax Check Results\n"
        )
        if ex_in.python_parse_error or ex_in.sql_parse_error:
            notebook_content += (
                f"# MAGIC These are errors from static syntax checks.\n"
                f"# MAGIC Manual corrections are required for these errors.\n"
            )
            if ex_in.python_parse_error:
                notebook_content += (
                    f"# MAGIC ### Python Syntax Errors\n"
                    f"# MAGIC ```\n"
                    f"# MAGIC {ex_in.python_parse_error}\n"
                    f"# MAGIC ```\n"
                )
            if ex_in.sql_parse_error:
                notebook_content += (
                    f"# MAGIC ### Spark SQL Syntax Errors\n"
                    f"# MAGIC ```\n"
                )
                for error in ex_in.sql_parse_error:
                    notebook_content += f"# MAGIC {error}\n"
                notebook_content += f"# MAGIC ```\n"
        else:
            notebook_content += (
                f"# MAGIC No syntax errors were detected during the static check.\n"
                f"# MAGIC However, please review the code carefully as some issues may only be detected during runtime.\n"
            )
        return notebook_content

    def generate_unique_output_paths(self, exporter_inputs: List[ExportInput]) -> List[str]:
        """
        Generates unique output file paths by appending a number if the file already exists.
        The number is incremented from 1 until a unique path is found.
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
