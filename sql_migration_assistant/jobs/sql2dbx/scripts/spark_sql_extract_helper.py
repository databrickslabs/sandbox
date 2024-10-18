import ast
from typing import List, Optional, Tuple, Union


class SparkSQLExtractHelper:
    """A class to extract Spark SQL statements from a given Python function string."""

    def __init__(self) -> None:
        self.sql_statements: List[str] = []
        self.variables: dict = {}

    def extract_sql_from_string(self, func_string: str) -> Tuple[Optional[str], List[str]]:
        """
        Parses a Python function string and extracts Spark SQL statements.

        Args:
            func_string (str): The Python function as a string.

        Returns:
            Tuple[Optional[str], List[str]]: A tuple containing an optional error message and a list of extracted SQL statements.
        """
        try:
            tree = ast.parse(func_string)
        except SyntaxError as e:
            return str(e), []
        try:
            self.visit(tree)
            cleaned_statements = [self.clean_sql(sql) for sql in self.sql_statements]
            return None, cleaned_statements
        except Exception as e:
            return str(e), []

    def clean_sql(self, sql: str) -> str:
        """
        Cleans the extracted SQL statement by removing newline characters, trimming spaces,
        and removing curly braces.

        Args:
            sql (str): The extracted SQL statement.

        Returns:
            str: The cleaned SQL statement.
        """
        cleaned_sql = sql.replace('\n', ' ').replace('\r', ' ').strip()
        cleaned_sql = cleaned_sql.replace('{', '').replace('}', '')
        return cleaned_sql

    def visit(self, node: ast.AST) -> None:
        """
        Visits each node in the AST tree and processes relevant nodes.

        Args:
            node (ast.AST): The root node of the AST tree.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                self.visit_assign(child)
            elif isinstance(child, ast.Call):
                self.visit_call(child)

    def visit_assign(self, node: ast.Assign) -> None:
        """
        Processes assignment nodes to extract variable values.

        Args:
            node (ast.Assign): An assignment node in the AST tree.
        """
        if isinstance(node.targets[0], ast.Name):
            value = self.extract_value(node.value)
            if value:
                self.variables[node.targets[0].id] = value

    def extract_value(self, node: ast.AST) -> Optional[str]:
        """
        Extracts the value from a given AST node.

        Args:
            node (ast.AST): An AST node.

        Returns:
            Optional[str]: The extracted value as a string, or None if the value could not be extracted.
        """
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.JoinedStr):
            return self.process_f_string(node)
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, "_placeholder_")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self.extract_value(node.left)
            right = self.extract_value(node.right)
            if left and right:
                return left + right
        return None

    def process_f_string(self, node: ast.JoinedStr) -> str:
        """
        Processes an f-string node to extract its value.

        Args:
            node (ast.JoinedStr): An f-string node in the AST tree.

        Returns:
            str: The extracted f-string value.
        """
        return ''.join(self.process_f_string_part(v) for v in node.values)

    def process_f_string_part(self, part: Union[ast.Constant, ast.FormattedValue]) -> str:
        """
        Processes a part of an f-string node.

        Args:
            part (Union[ast.Constant, ast.FormattedValue]): A part of an f-string node.

        Returns:
            str: The extracted value as a string.
        """
        if isinstance(part, ast.Constant):
            return str(part.value)
        elif isinstance(part, ast.FormattedValue):
            value = self.extract_value(part.value)
            if value and isinstance(part.value, ast.Name):
                return str(self.variables.get(part.value.id, "_placeholder_"))
            return f"{value}" if value else "_placeholder_"
        else:
            return str(part)

    def visit_call(self, node: ast.Call) -> None:
        """
        Processes call nodes to extract Spark SQL statements.

        Args:
            node (ast.Call): A call node in the AST tree.
        """
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'sql' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'spark':
            if len(node.args) == 1:
                arg = node.args[0]
                sql = self.extract_value(arg)
                if sql:
                    self.sql_statements.append(sql)


# Usage example
if __name__ == "__main__":
    helper = SparkSQLExtractHelper()
    error, sql_statements = helper.extract_sql_from_string("""
    def example_func():
        query = "SELECT * FROM {table}"
        spark.sql(query)
    """)
    if error:
        print("Error:", error)
    else:
        print("SQL Statements:", sql_statements)
