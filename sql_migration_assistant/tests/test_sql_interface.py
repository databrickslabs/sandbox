import unittest
from unittest.mock import MagicMock, patch
from app.sql_interface import SQLInterface  # replace 'your_module' with the actual name of your module


class TestSQLInterface(unittest.TestCase):
    """
    Unit test class for testing the SQLInterface class.
    """

    @patch('app.sql_interface.sql.connect')
    def setUp(self, mock_sql_connect):
        """
        Sets up the test case by initializing an instance of SQLInterface with mock dependencies.

        Mocking the sql.connect method to isolate the functionality of SQLInterface from external dependencies.
        """
        # Mock the connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor
        mock_sql_connect.return_value = self.mock_connection

        # Initialize the SQLInterface instance with mock parameters
        self.sql_interface = SQLInterface(
            databricks_host='test_host',
            databricks_token='test_token',
            sql_warehouse_http_path='test_http_path'
        )

    def test_execute_sql(self):
        """
        Tests the execute_sql method of SQLInterface class.

        This test ensures that the SQL statement is executed and the fetched results are returned correctly.
        """
        # Mock the execute and fetchall methods
        self.mock_cursor.execute.return_value = None
        self.mock_cursor.fetchall.return_value = [('result1',), ('result2',)]

        # SQL statement to test
        sql_statement = "SELECT * FROM test_table"

        # Call the method to test
        results = self.sql_interface.execute_sql(self.mock_cursor, sql_statement)

        # Assert that the execute method was called with the correct SQL statement
        self.mock_cursor.execute.assert_called_once_with(sql_statement)

        # Assert that fetchall method was called and returned the expected results
        self.mock_cursor.fetchall.assert_called_once()
        self.assertEqual(results, [('result1',), ('result2',)])


if __name__ == '__main__':
    unittest.main()
