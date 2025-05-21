import os
import tempfile
import unittest
from pathlib import Path

import yaml

from notebooks.pyscripts.conversion_prompt_helper import (
    ConversionPromptHelper, PromptConfig, SupportedSQLDialect)


class TestSupportedSQLDialect(unittest.TestCase):
    def test_enum_values(self):
        """Test that the SupportedSQLDialect enum contains the expected values."""
        self.assertEqual(SupportedSQLDialect.POSTGRESQL.name, "POSTGRESQL")
        self.assertEqual(SupportedSQLDialect.SNOWFLAKE.name, "SNOWFLAKE")
        self.assertEqual(SupportedSQLDialect.TSQL.name, "TSQL")

        # Test the dialect_name property
        self.assertEqual(SupportedSQLDialect.POSTGRESQL.dialect_name, "postgresql")
        self.assertEqual(SupportedSQLDialect.SNOWFLAKE.dialect_name, "snowflake")
        self.assertEqual(SupportedSQLDialect.TSQL.dialect_name, "tsql")

        # Test the default_yaml_filename property
        self.assertEqual(SupportedSQLDialect.POSTGRESQL.default_yaml_filename,
                         "postgresql_to_databricks_notebook.yml")
        self.assertEqual(SupportedSQLDialect.SNOWFLAKE.default_yaml_filename,
                         "snowflake_to_databricks_notebook.yml")
        self.assertEqual(SupportedSQLDialect.TSQL.default_yaml_filename,
                         "tsql_to_databricks_notebook.yml")

    def test_get_supported_sql_dialects(self):
        """Test that get_supported_sql_dialects returns all expected dialects."""
        dialects = ConversionPromptHelper.get_supported_sql_dialects()

        # Check that all expected dialects are present
        self.assertIn("mysql", dialects)
        self.assertIn("netezza", dialects)
        self.assertIn("oracle", dialects)
        self.assertIn("postgresql", dialects)
        self.assertIn("redshift", dialects)
        self.assertIn("snowflake", dialects)
        self.assertIn("tsql", dialects)
        self.assertIn("teradata", dialects)

        # Check the total count to ensure no extras or missing ones
        self.assertEqual(len(dialects), 8)

    def test_get_default_yaml_for_sql_dialect(self):
        """Test that get_default_yaml_for_sql_dialect returns the correct paths."""
        # Test for postgresql
        postgresql_path = ConversionPromptHelper.get_default_yaml_for_sql_dialect("postgresql")
        self.assertIsInstance(postgresql_path, str)
        self.assertTrue(postgresql_path.endswith("postgresql_to_databricks_notebook.yml"))

        # Test for snowflake
        snowflake_path = ConversionPromptHelper.get_default_yaml_for_sql_dialect("snowflake")
        self.assertIsInstance(snowflake_path, str)
        self.assertTrue(snowflake_path.endswith("snowflake_to_databricks_notebook.yml"))

        # Test for tsql
        tsql_path = ConversionPromptHelper.get_default_yaml_for_sql_dialect("tsql")
        self.assertIsInstance(tsql_path, str)
        self.assertTrue(tsql_path.endswith("tsql_to_databricks_notebook.yml"))

        # Test with invalid dialect
        with self.assertRaises(ValueError) as context:
            ConversionPromptHelper.get_default_yaml_for_sql_dialect("invalid_dialect")
        self.assertIn("Unsupported sql dialect", str(context.exception))

    def test_path_resolution(self):
        """Test that the path resolution for YAML files works correctly."""
        for dialect in SupportedSQLDialect:
            yaml_path = ConversionPromptHelper.get_default_yaml_for_sql_dialect(dialect.dialect_name)
            # The path should be an absolute path
            self.assertTrue(Path(yaml_path).is_absolute())
            # The path should include the dialect-specific filename
            self.assertTrue(yaml_path.endswith(dialect.default_yaml_filename))


class TestConversionPromptHelper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.valid_yaml_content = {
            "system_message": "Convert SQL to Python ({comment_lang} comments)",
            "few_shots": [
                {
                    "role": "user",
                    "content": "Sample SQL"
                },
                {
                    "role": "assistant",
                    "content": "Sample Python"
                }
            ]
        }
        self.valid_yaml_path = os.path.join(self.temp_dir, "valid_prompt.yml")
        with open(self.valid_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.valid_yaml_content, f)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)

    def test_conversion_prompt_helper_initialization(self):
        """Test that ConversionPromptHelper initializes correctly"""
        helper = ConversionPromptHelper(self.valid_yaml_path, "ja")
        self.assertIsInstance(helper, ConversionPromptHelper)
        self.assertIsInstance(helper.prompt_config, PromptConfig)

    def test_get_system_message(self):
        """Test that get_system_message returns the correct message"""
        helper = ConversionPromptHelper(self.valid_yaml_path, "ja")
        expected = "Convert SQL to Python (ja comments)"
        self.assertEqual(helper.get_system_message(), expected)

    def test_get_few_shots(self):
        """Test that get_few_shots returns the correct few-shot examples"""
        helper = ConversionPromptHelper(self.valid_yaml_path, "ja")
        few_shots = helper.get_few_shots()
        self.assertEqual(len(few_shots), 2)
        self.assertEqual(few_shots[0]["role"], "user")
        self.assertEqual(few_shots[0]["content"], "Sample SQL")
        self.assertEqual(few_shots[1]["role"], "assistant")
        self.assertEqual(few_shots[1]["content"], "Sample Python")

    def test_non_existent_yaml_file(self):
        """Test that FileNotFoundError is raised when YAML file does not exist"""
        with self.assertRaises(Exception) as context:
            ConversionPromptHelper("non_existent.yml", "ja")
        self.assertIn("YAML file not found", str(context.exception))

    def test_invalid_yaml_content(self):
        """Test that ValueError is raised when YAML content is not a dictionary"""
        invalid_yaml_path = os.path.join(self.temp_dir, "invalid_prompt.yml")
        with open(invalid_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(["invalid", "content"], f)

        with self.assertRaises(Exception) as context:
            ConversionPromptHelper(invalid_yaml_path, "ja")
        self.assertIn("YAML content must be a dictionary", str(context.exception))

    def test_missing_system_message(self):
        """Test that ValueError is raised when system_message key is missing"""
        invalid_yaml_path = os.path.join(self.temp_dir, "missing_system_message.yml")
        with open(invalid_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump({"few_shots": []}, f)

        with self.assertRaises(Exception) as context:
            ConversionPromptHelper(invalid_yaml_path, "ja")
        self.assertIn("YAML must contain 'system_message' key", str(context.exception))

    def test_yaml_without_few_shots(self):
        """Test that empty list is returned when few_shots key is missing"""
        yaml_path = os.path.join(self.temp_dir, "no_few_shots.yml")
        content = {"system_message": "Test message"}
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(content, f)

        helper = ConversionPromptHelper(yaml_path, "ja")
        self.assertEqual(helper.get_few_shots(), [])

    def test_tsql_to_databricks_yaml(self):
        """Test loading and parsing tsql_to_databricks_notebook.yml"""
        yaml_path = ConversionPromptHelper.get_default_yaml_for_sql_dialect("tsql")
        helper = ConversionPromptHelper(yaml_path, "ja")
        system_message = helper.get_system_message()
        self.assertIn("Instructions", system_message)


if __name__ == '__main__':
    unittest.main()
