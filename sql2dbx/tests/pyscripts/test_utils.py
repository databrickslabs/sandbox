import os
import tempfile
import unittest

from notebooks.pyscripts.utils import (get_file_content,
                                       list_files_recursively,
                                       parse_number_ranges,
                                       remove_sql_comments)


class TestUtils(unittest.TestCase):
    def test_remove_sql_comments(self):
        sql_text = "SELECT * FROM table; -- This is a comment\n/* Block comment */\nSELECT * FROM another_table;"
        cleaned_sql = remove_sql_comments(sql_text)
        expected_sql = "SELECT * FROM table; \n\nSELECT * FROM another_table;"
        self.assertEqual(cleaned_sql, expected_sql)

    def test_list_files_recursively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = os.path.join(temp_dir, "file1.sql")
            file2 = os.path.join(temp_dir, "file2.sql")
            subdir = os.path.join(temp_dir, "subdir")
            os.mkdir(subdir)
            file3 = os.path.join(subdir, "file3.sql")

            with open(file1, 'w') as f:
                f.write("SELECT 1;")
            with open(file2, 'w') as f:
                f.write("SELECT 2;")
            with open(file3, 'w') as f:
                f.write("SELECT 3;")

            all_files = list_files_recursively(temp_dir)
            self.assertIn(file1, all_files)
            self.assertIn(file2, all_files)
            self.assertIn(file3, all_files)

    def test_get_file_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "file.sql")
            content = "This is test; これはテストです。"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            file_content, encoding = get_file_content(file_path)
            self.assertEqual(file_content, content)
            self.assertEqual(encoding, 'utf-8')

            # Test with specified encoding
            file_content, encoding = get_file_content(file_path, encoding='utf-8')
            self.assertEqual(file_content, content)
            self.assertEqual(encoding, 'utf-8')


class TestParseNumberRanges(unittest.TestCase):
    """Test cases for the parse_number_ranges function."""

    def test_single_integer(self):
        """Test parsing a single integer."""
        self.assertEqual(parse_number_ranges("5"), [5])

    def test_single_range(self):
        """Test parsing a single range."""
        self.assertEqual(parse_number_ranges("2-6"), [2, 3, 4, 5, 6])

    def test_multiple_integers(self):
        """Test parsing multiple integers."""
        self.assertEqual(parse_number_ranges("1,3,8"), [1, 3, 8])

    def test_multiple_ranges(self):
        """Test parsing multiple ranges."""
        self.assertEqual(parse_number_ranges("1-3,5-7"), [1, 2, 3, 5, 6, 7])

    def test_mixed_integers_and_ranges(self):
        """Test parsing a mix of integers and ranges."""
        self.assertEqual(parse_number_ranges("2,4-6,9"), [2, 4, 5, 6, 9])

    def test_empty_string(self):
        """Test parsing an empty string."""
        self.assertEqual(parse_number_ranges(""), [])

    # Invalid input format tests
    def test_invalid_range(self):
        """Test parsing an invalid range (e.g., '1-3-5')."""
        with self.assertRaises(ValueError):
            parse_number_ranges("1-3-5")

    def test_non_numeric_input(self):
        """Test parsing non-numeric input."""
        with self.assertRaises(ValueError):
            parse_number_ranges("1,a,3")


if __name__ == '__main__':
    unittest.main()
