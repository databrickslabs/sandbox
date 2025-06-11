import unittest

from notebooks.pyscripts.conversion_result_clean_helper import \
    ConversionResultCleanHelper


class TestConversionResultCleanHelper(unittest.TestCase):
    def setUp(self):
        self.helper = ConversionResultCleanHelper()

    def test_none_input(self):
        """Test that None input returns None."""
        self.assertIsNone(self.helper.clean_python_code_blocks(None))

    def test_no_python_markers(self):
        """Test text without any ```python markers."""
        text = "This is just regular text without any code blocks."
        self.assertEqual(self.helper.clean_python_code_blocks(text), text)

    def test_starts_with_python_marker(self):
        """Test text that starts with ```python and has a closing ```."""
        text = """```python
def hello():
    print("Hello, world!")
```
Some extra text after the code block."""

        expected = """def hello():
    print("Hello, world!")
"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_starts_with_whitespace_then_python_marker(self):
        """Test text that starts with whitespace followed by ```python."""
        text = """  
  ```python
def hello():
    print("Hello, world!")
```
Some extra text after the code block."""

        expected = """def hello():
    print("Hello, world!")
"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_python_marker_in_middle(self):
        """Test text with ```python in the middle."""
        text = """columns.customer_id```python columns.order_id, columns.product_id, columns.timestamp"""
        expected = """columns.customer_id columns.order_id, columns.product_id, columns.timestamp"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_sql_with_python_marker_in_middle(self):
        """Test SQL query with ```python in the middle."""
        text = """# Creating a temporary view
spark.sql(\"\"\"
    CREATE OR REPLACE TEMPORARY VIEW sales_data AS
    SELECT DISTINCT
        data.year,
        data.month,
        data.day,
        data.region,
        data.store,
        data.product,
        data.category,
        data.quantity,
        data.price,
        data.total_sales```python
        data.discount,
        data.promotion,
        data.customer_segment,
        data.profit\"\"\")"""

        expected = """# Creating a temporary view
spark.sql(\"\"\"
    CREATE OR REPLACE TEMPORARY VIEW sales_data AS
    SELECT DISTINCT
        data.year,
        data.month,
        data.day,
        data.region,
        data.store,
        data.product,
        data.category,
        data.quantity,
        data.price,
        data.total_sales
        data.discount,
        data.promotion,
        data.customer_segment,
        data.profit\"\"\")"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_starts_with_python_no_closing_marker(self):
        """Test text that starts with ```python but has no closing ```."""
        text = """```python
def hello():
    print("Hello, world!")
This continues without a closing marker."""

        expected = """
def hello():
    print("Hello, world!")
This continues without a closing marker."""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_indented_code_block(self):
        """Test that indentation is preserved in extracted code."""
        text = """```python
    def hello():
        print("Hello, world!")
        if True:
            print("Indented")
```"""

        expected = """    def hello():
        print("Hello, world!")
        if True:
            print("Indented")
"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)

    def test_text_before_python_marker(self):
        """Test with text before ```python marker."""
        text = """Filter condition:
    ```python
    if data['status'] == 'active' and data['value'] > 100:
        return True
    else:
        return False"""

        expected = """Filter condition:
    
    if data['status'] == 'active' and data['value'] > 100:
        return True
    else:
        return False"""
        self.assertEqual(self.helper.clean_python_code_blocks(text), expected)


if __name__ == '__main__':
    unittest.main()
