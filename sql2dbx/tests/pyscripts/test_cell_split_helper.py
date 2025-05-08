import unittest
import textwrap

from notebooks.pyscripts.cell_split_helper import CellSplitHelper


class TestCellSplitHelperTopLevel(unittest.TestCase):
    def setUp(self):
        self.helper = CellSplitHelper()

    def test_empty_code(self):
        """
        Test case for empty code input. Expected to return None.
        """
        code = ""
        result = self.helper.split_cells(code)
        self.assertIsNone(result)

    def test_none_input(self):
        """
        Test case for None input. Expected to return None.
        """
        code = None
        result = self.helper.split_cells(code)
        self.assertIsNone(result)

    def test_syntax_error_code(self):
        """
        Test case for code with syntax error.
        Checks how it's handled - possibly returning "COMMAND marker + code" on parse failure.
        """
        code = "if True:\n"  # Unclosed block
        result = self.helper.split_cells(code)
        # Verify that the result is not None and contains COMMAND_MARKER
        self.assertIsNotNone(result)
        self.assertIn(self.helper.COMMAND_MARKER, result)
        self.assertIn("if True:", result)

    def test_basic_single_statement(self):
        """
        Test case for a single top-level statement.
        Example: Assign + print
        """
        code = textwrap.dedent("""\
            var1 = 1
            print(var1)
        """)
        result = self.helper.split_cells(code)
        lines = result.split("\n")
        self.assertEqual(lines[0], self.helper.COMMAND_MARKER)
        self.assertEqual(lines[1], "var1 = 1")
        self.assertEqual(lines[2], "print(var1)")

    def test_code_with_leading_comments(self):
        """
        Test case for code with leading comments.
        Verify that comments are included in the same block.
        """
        code = textwrap.dedent("""\
            # leading comment
            var1 = 1
            var2 = 2
        """)
        result = self.helper.split_cells(code)
        lines = result.split("\n")
        self.assertEqual(lines[0], self.helper.COMMAND_MARKER)
        self.assertEqual(lines[1], "# leading comment")
        self.assertEqual(lines[2], "var1 = 1")
        self.assertEqual(lines[3], "var2 = 2")

    def test_top_level_splitting_example(self):
        """
        Test case for a larger sample to verify expected cell splitting.
        """
        code = textwrap.dedent("""\
            # Some initial vars
            var1 = 1
            var2 = 2

            # If block
            if var1 < 10:
                var2 = spark.sql("SELECT * FROM table WHERE col < 10")
                display(var2)

            # Widgets
            dbutils.widgets.text("paramA", "valA")
            dbutils.widgets.text("paramB", "valB")

            # Another top-level statement
            var3 = var1 + var2.count()

            # Try-except block
            try:
                var4 = spark.sql("SELECT 100")
            except:
                pass

            # For block
            for i in range(3):
                print(i)

            # Finally exit
            dbutils.notebook.exit("Done")
        """)
        expected = textwrap.dedent(f"""\
            {self.helper.COMMAND_MARKER}
            # Some initial vars
            var1 = 1
            var2 = 2

            {self.helper.COMMAND_MARKER}
            # If block
            if var1 < 10:
                var2 = spark.sql("SELECT * FROM table WHERE col < 10")
                display(var2)

            {self.helper.COMMAND_MARKER}
            # Widgets
            dbutils.widgets.text("paramA", "valA")
            dbutils.widgets.text("paramB", "valB")

            {self.helper.COMMAND_MARKER}
            # Another top-level statement
            var3 = var1 + var2.count()

            {self.helper.COMMAND_MARKER}
            # Try-except block
            try:
                var4 = spark.sql("SELECT 100")
            except:
                pass

            {self.helper.COMMAND_MARKER}
            # For block
            for i in range(3):
                print(i)

            {self.helper.COMMAND_MARKER}
            # Finally exit
            dbutils.notebook.exit("Done")
        """)
        result = self.helper.split_cells(code)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
