import os
import tempfile
import unittest

from notebooks.pyscripts.llm_token_count_helper import (FileTokenCountHelper,
                                                        FileTokenMetadata)
from notebooks.pyscripts.token_utils import (ClaudeTokenCounter,
                                             OpenAITokenCounter)


class TestFileTokenCountHelper(unittest.TestCase):
    def test_init_with_endpoint_name(self):
        # Use Databricks Claude endpoint
        helper = FileTokenCountHelper(endpoint_name="databricks-claude-3-7-sonnet")
        self.assertEqual(helper.tokenizer_type, "claude")
        self.assertEqual(helper.tokenizer_model, "claude")
        self.assertIsInstance(helper.token_counter, ClaudeTokenCounter)

        # Use OpenAI endpoint
        helper = FileTokenCountHelper(endpoint_name="gpt-4o")
        self.assertEqual(helper.tokenizer_type, "openai")
        self.assertEqual(helper.tokenizer_model, "o200k_base")
        self.assertIsInstance(helper.token_counter, OpenAITokenCounter)

        # Use other
        helper = FileTokenCountHelper(endpoint_name="other")
        self.assertEqual(helper.tokenizer_type, "openai")
        self.assertEqual(helper.tokenizer_model, "o200k_base")
        self.assertIsInstance(helper.token_counter, OpenAITokenCounter)

    def test_init_with_explicit_tokenizer(self):
        # Explicitly specify OpenAI tokenizer
        helper = FileTokenCountHelper(tokenizer_type="openai", tokenizer_model="o200k_base")
        self.assertEqual(helper.tokenizer_type, "openai")
        self.assertEqual(helper.tokenizer_model, "o200k_base")
        self.assertIsInstance(helper.token_counter, OpenAITokenCounter)

        # Explicitly specify Claude tokenizer
        helper = FileTokenCountHelper(tokenizer_type="claude")
        self.assertEqual(helper.tokenizer_type, "claude")
        self.assertEqual(helper.tokenizer_model, "claude")
        self.assertIsInstance(helper.token_counter, ClaudeTokenCounter)

    def test_default_init(self):
        # Default settings (Claude tokenizer)
        helper = FileTokenCountHelper()
        self.assertEqual(helper.tokenizer_type, "claude")
        self.assertEqual(helper.tokenizer_model, "claude")
        self.assertIsInstance(helper.token_counter, ClaudeTokenCounter)

    def test_process_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test SQL file
            file_path = os.path.join(temp_dir, "test.sql")
            with open(file_path, 'w') as f:
                f.write("SELECT * FROM table; -- comment\n/* block comment */\nSELECT * FROM another_table;")

            # Process file using Claude tokenizer
            helper = FileTokenCountHelper(tokenizer_type="claude")
            metadata = helper.process_file(file_path)

            # Validate metadata
            self.assertEqual(metadata.input_file_path, file_path)
            self.assertGreater(metadata.input_file_token_count, 0)
            self.assertIsNotNone(metadata.input_file_content_without_sql_comments)
            self.assertGreater(metadata.input_file_token_count, metadata.input_file_token_count_without_sql_comments)
            self.assertEqual(metadata.tokenizer_type, "claude")

    def test_process_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test SQL files
            file1 = os.path.join(temp_dir, "file1.sql")
            file2 = os.path.join(temp_dir, "file2.sql")

            with open(file1, 'w') as f:
                f.write("SELECT * FROM table1;")
            with open(file2, 'w') as f:
                f.write("SELECT * FROM table2;")

            # Process directory files
            helper = FileTokenCountHelper(tokenizer_type="claude")
            results = helper.process_directory(temp_dir)

            # Validate results
            self.assertEqual(len(results), 2)
            self.assertIsInstance(results[0], FileTokenMetadata)
            self.assertIsInstance(results[1], FileTokenMetadata)

            # Verify file numbers are set correctly
            file_numbers = [result.input_file_number for result in results]
            self.assertIn(1, file_numbers)
            self.assertIn(2, file_numbers)


if __name__ == '__main__':
    unittest.main()
