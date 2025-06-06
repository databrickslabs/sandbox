import unittest

from notebooks.pyscripts.spark_sql_extract_helper import SparkSQLExtractHelper


class TestSparkSQLExtractor(unittest.TestCase):

    def setUp(self) -> None:
        self.helper = SparkSQLExtractHelper()

    def test_simple_sql_extraction(self):
        func_string = (
            "def example_func():\n"
            "    query = \"SELECT * FROM table\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table"])

    def test_multiple_sql_extractions(self):
        func_string = (
            "def example_func():\n"
            "    query1 = \"SELECT * FROM table1\"\n"
            "    query2 = \"SELECT * FROM table2\"\n"
            "    spark.sql(query1)\n"
            "    spark.sql(query2)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table1", "SELECT * FROM table2"])

    def test_f_string_extraction(self):
        func_string = (
            "def example_func():\n"
            "    table_name = \"table\"\n"
            "    query = f\"SELECT * FROM {table_name}\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table"])

    def test_syntax_error(self):
        func_string = (
            "def example_func()\n"
            "    query = \"SELECT * FROM table\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertTrue(error)
        self.assertEqual(sql_statements, [])

    def test_variable_assignment(self):
        func_string = (
            "def example_func():\n"
            "    table_name = \"table\"\n"
            "    query = \"SELECT * FROM \" + table_name\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table"])

    def test_placeholder_replacement(self):
        func_string = (
            "def example_func():\n"
            "    table_name = \"table\"\n"
            "    query = f\"SELECT * FROM {table_name} WHERE column = {_placeholder_}\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table WHERE column = _placeholder_"])

    def test_curly_braces_removal(self):
        func_string = (
            "def example_func():\n"
            "    query = \"SELECT * FROM {table}\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table"])

    # Tests for None and non-string inputs
    def test_none_input(self):
        """Test handling of None input."""
        error, sql_statements = self.helper.extract_sql_from_string(None)
        self.assertIsNone(error)  # Should return None for error to be consistent with success case
        self.assertEqual(sql_statements, [])

    def test_non_string_input_number(self):
        """Test handling of non-string input (number)."""
        error, sql_statements = self.helper.extract_sql_from_string(42)
        self.assertEqual(error, "Type error during parsing: compile() arg 1 must be a string, bytes or AST object")
        self.assertEqual(sql_statements, [])

    def test_non_string_input_list(self):
        """Test handling of non-string input (list)."""
        error, sql_statements = self.helper.extract_sql_from_string(["SELECT * FROM table"])
        self.assertEqual(error, "Type error during parsing: compile() arg 1 must be a string, bytes or AST object")
        self.assertEqual(sql_statements, [])

    def test_empty_string_input(self):
        """Test handling of empty string input."""
        error, sql_statements = self.helper.extract_sql_from_string("")
        # Empty string is technically valid Python syntax, but will not yield SQL
        self.assertIsNone(error)
        self.assertEqual(sql_statements, [])

    def test_whitespace_only_input(self):
        """Test handling of whitespace-only string input."""
        error, sql_statements = self.helper.extract_sql_from_string("   \n   \t   ")
        # Whitespace is also valid Python syntax
        self.assertIsNone(error)
        self.assertEqual(sql_statements, [])

    # Test for invalid Python code that's not a syntax error
    def test_valid_python_but_not_function(self):
        """Test handling of valid Python code that's not a function definition."""
        func_string = "x = 10\ny = 20\nprint(x + y)"
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)  # This is valid Python but may not have SQL
        self.assertEqual(sql_statements, [])

    # Test for multiple errors in the same function
    def test_multiple_syntax_errors(self):
        """Test handling of Python code with multiple syntax errors."""
        func_string = (
            "def example_func():\n"
            "    query = SELECT * FROM table\n"  # Missing quotes
            "    spark.sql(query\n"  # Missing closing parenthesis
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertTrue(error)
        self.assertTrue(error.startswith("Python syntax error:"))
        self.assertEqual(sql_statements, [])

    # Test for SQL with special characters
    def test_sql_with_special_characters(self):
        """Test extraction of SQL with special characters."""
        func_string = (
            "def example_func():\n"
            "    query = \"SELECT * FROM table WHERE col1 LIKE '%special\\\\%'\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM table WHERE col1 LIKE '%special\\%'"])

    # Test for complex variable interpolation in f-strings
    def test_complex_f_string_interpolation(self):
        """Test extraction of SQL from complex f-string interpolation."""
        func_string = (
            "def example_func():\n"
            "    schema = \"public\"\n"
            "    table = \"users\"\n"
            "    conditions = \"age > 18\"\n"
            "    query = f\"SELECT * FROM {schema}.{table} WHERE {conditions}\"\n"
            "    spark.sql(query)\n"
        )
        error, sql_statements = self.helper.extract_sql_from_string(func_string)
        self.assertIsNone(error)
        self.assertEqual(sql_statements, ["SELECT * FROM public.users WHERE age > 18"])


if __name__ == "__main__":
    unittest.main()