import os
import unittest

from notebooks.pyscripts.notebook_export_helper import (ExportInput,
                                                        NotebookExportHelper)
from notebooks.pyscripts.notebook_i18n import MessageKey, get_language_messages

TEST_TEXT = """print("Hello, World!")

def foo():
    return "bar"
"""


class TestNotebookExportHelper(unittest.TestCase):
    """Test cases for the NotebookExportHelper class."""

    def setUp(self):
        """Set up test fixtures."""
        self.helper = NotebookExportHelper()
        self.test_text = TEST_TEXT
        self.input_file_path = "test_input_file.txt"
        self.output_dir = "dummy_output_dir"
        self.comment_lang = "English"

    def test_create_notebook_content(self):
        """Test creating notebook content with basic input."""
        code = 'print("Hello, World!")'
        output_file_path = "test_output_file"
        ex_in = ExportInput(input_file_path=self.input_file_path, code=code,
                            output_dir=self.output_dir, comment_lang=self.comment_lang)
        content = self.helper.create_notebook_content(output_file_path, ex_in)
        messages = get_language_messages(self.comment_lang)

        self.assertTrue(content.startswith("# Databricks notebook source"))
        self.assertIn(code, content)
        self.assertIn(self.input_file_path, content)
        self.assertIn(messages[MessageKey.SYNTAX_CHECK_RESULTS], content)
        self.assertIn(messages[MessageKey.NO_ERRORS_DETECTED], content)
        self.assertIn(messages[MessageKey.REVIEW_CODE], content)

    def test_create_notebook_content_with_errors(self):
        """Test creating notebook content with Python and SQL errors."""
        code = 'print("Hello, World!")'
        output_file_path = "test_output_file"
        python_error = "SyntaxError: invalid syntax"
        sql_errors = ["Error in SQL query", "Another SQL error"]
        ex_in = ExportInput(input_file_path=self.input_file_path, code=code, output_dir=self.output_dir,
                            comment_lang=self.comment_lang, python_parse_error=python_error, sql_parse_error=sql_errors)
        content = self.helper.create_notebook_content(output_file_path, ex_in)
        messages = get_language_messages(self.comment_lang)

        self.assertIn(messages[MessageKey.SYNTAX_CHECK_RESULTS], content)
        self.assertIn(messages[MessageKey.ERRORS_FROM_CHECKS], content)
        self.assertIn(messages[MessageKey.PYTHON_SYNTAX_ERRORS], content)
        self.assertIn(python_error, content)
        self.assertIn(messages[MessageKey.SPARK_SQL_SYNTAX_ERRORS], content)
        for error in sql_errors:
            self.assertIn(error, content)

    def test_create_notebook_content_without_errors(self):
        """Test creating notebook content without errors."""
        code = 'print("Hello, World!")'
        output_file_path = "test_output_file"
        ex_in = ExportInput(input_file_path=self.input_file_path, code=code,
                            output_dir=self.output_dir, comment_lang=self.comment_lang)
        content = self.helper.create_notebook_content(output_file_path, ex_in)
        messages = get_language_messages(self.comment_lang)

        self.assertIn(messages[MessageKey.SYNTAX_CHECK_RESULTS], content)
        self.assertIn(messages[MessageKey.NO_ERRORS_DETECTED], content)
        self.assertIn(messages[MessageKey.REVIEW_CODE], content)
        self.assertNotIn(messages[MessageKey.ERRORS_FROM_CHECKS], content)

    def test_generate_unique_output_paths(self):
        """Test generating unique output paths when duplicate inputs exist."""
        exporter_inputs = [
            ExportInput(input_file_path="test_input_file.txt", code=self.test_text,
                        output_dir=self.output_dir, comment_lang=self.comment_lang),
            ExportInput(input_file_path="test_input_file.txt", code=self.test_text,
                        output_dir=self.output_dir, comment_lang=self.comment_lang),
            ExportInput(input_file_path="test_input_file.txt", code=self.test_text,
                        output_dir=self.output_dir, comment_lang=self.comment_lang)
        ]
        expected_paths = [
            os.path.join(self.output_dir, "test_input_file"),
            os.path.join(self.output_dir, "test_input_file_1"),
            os.path.join(self.output_dir, "test_input_file_2")
        ]
        unique_paths = self.helper.generate_unique_output_paths(exporter_inputs)
        self.assertEqual(unique_paths, expected_paths)

    def test_process_notebooks(self):
        """Test processing multiple notebooks."""
        exporter_inputs = [
            ExportInput(input_file_path="test_input_file1.txt", code=self.test_text,
                        output_dir=self.output_dir, comment_lang=self.comment_lang),
            ExportInput(input_file_path="test_input_file2.txt", code=self.test_text,
                        output_dir=self.output_dir, comment_lang=self.comment_lang)
        ]
        results = self.helper.process_notebooks(exporter_inputs)

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertTrue(isinstance(result.base64_encoded_content, str))
            self.assertTrue(isinstance(result.base64_encoded_content_size, int))
            self.assertTrue(result.output_file_path.startswith(self.output_dir))
            self.assertTrue(result.export_succeeded)

    def test_different_languages(self):
        """Test notebook creation with all supported languages."""
        languages = ["English", "Japanese", "French", "German", "Italian", "Spanish", "Chinese", "Korean", "Portuguese"]
        code = 'print("Hello, World!")'
        output_file_path = "test_output_file"

        for lang in languages:
            ex_in = ExportInput(input_file_path=self.input_file_path, code=code,
                                output_dir=self.output_dir, comment_lang=lang)
            content = self.helper.create_notebook_content(output_file_path, ex_in)
            messages = get_language_messages(lang)

            self.assertIn(messages[MessageKey.NOTEBOOK_DESCRIPTION], content)
            self.assertIn(messages[MessageKey.SOURCE_SCRIPT], content)
            self.assertIn(messages[MessageKey.SYNTAX_CHECK_RESULTS], content)
            self.assertIn(messages[MessageKey.NO_ERRORS_DETECTED], content)
            self.assertIn(messages[MessageKey.REVIEW_CODE], content)


if __name__ == '__main__':
    unittest.main()
