import unittest
from unittest.mock import MagicMock, patch
from app.similar_code import SimilarCode  # replace 'your_module' with the actual name of your module


class TestSimilarCode(unittest.TestCase):
    """
    Unit test class for testing the SimilarCode class.
    """

    @patch('app.similar_code.VectorSearchClient')
    def setUp(self, MockVectorSearchClient):
        """
        Sets up the test case by initializing an instance of SimilarCode with mock dependencies.

        Mocking the VectorSearchClient to isolate the functionality of SimilarCode from external dependencies.
        """
        self.mock_vsc_instance = MockVectorSearchClient.return_value
        self.similar_code = SimilarCode(
            databricks_token='test_token',
            databricks_host='test_host',
            vector_search_endpoint_name='test_endpoint',
            vs_index_fullname='test_index',
            intent_table='test_table'
        )

    def test_save_intent(self):
        """
        Tests the save_intent method of SimilarCode class.

        This test ensures that the SQL insert statement is correctly formed and executed with the provided parameters.
        """
        # Mock the database cursor
        mock_cursor = MagicMock()
        code = "sample code"
        intent = "sample intent"
        code_hash = hash(code)

        # Call the method to test
        self.similar_code.save_intent(code, intent, mock_cursor)

        # Assert that the execute method was called with the correct SQL statement
        mock_cursor.execute.assert_called_once_with(
            f"INSERT INTO test_table VALUES ({code_hash}, \"{code}\", \"{intent}\")"
        )

    def test_get_similar_code(self):
        """
        Tests the get_similar_code method of SimilarCode class.

        This test verifies that the method calls the VectorSearchClient with the correct parameters and
        returns the expected results.
        """
        # Sample chat history and mock result
        chat_history = [(1, "first intent"), (2, "second intent")]
        mock_result = {
            'result': {
                'data_array': [['sample code', 'sample intent']]
            }
        }

        # Mock the similarity_search method's return value
        self.mock_vsc_instance.get_index.return_value.similarity_search.return_value = mock_result

        # Call the method to test
        code, intent = self.similar_code.get_similar_code(chat_history)

        # Assert that get_index was called with the correct parameters
        self.mock_vsc_instance.get_index.assert_called_once_with('test_endpoint', 'test_index')

        # Assert that similarity_search was called with the correct parameters
        self.mock_vsc_instance.get_index.return_value.similarity_search.assert_called_once_with(
            query_text='second intent',
            columns=["code", "intent"],
            num_results=1
        )

        # Assert that the returned values are as expected
        self.assertEqual(code, 'sample code')
        self.assertEqual(intent, 'sample intent')


if __name__ == '__main__':
    unittest.main()
