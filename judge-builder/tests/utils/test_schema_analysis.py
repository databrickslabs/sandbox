"""Unit tests for schema analysis utility."""

import unittest
from unittest.mock import Mock, patch

from server.utils.schema_analysis import (
    extract_categorical_options_from_instruction,
    is_binary_categorical_options,
)


class TestSchemaAnalysis(unittest.TestCase):
    """Test cases for schema analysis functions."""

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_success(self, mock_context):
        """Test successful extraction of categorical options."""
        # Mock the managed_rag_client and response
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = '{"options": ["Pass", "Fail"]}'
        mock_client.get_chat_completions_result.return_value = mock_response
        
        # Test the function
        result = extract_categorical_options_from_instruction("Return pass if good, fail if bad")
        
        # Verify result
        self.assertEqual(result, ["Pass", "Fail"])
        mock_client.get_chat_completions_result.assert_called_once()

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_multi_option(self, mock_context):
        """Test extraction of multi-categorical options."""
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = '{"options": ["Poor", "Fair", "Good", "Excellent"]}'
        mock_client.get_chat_completions_result.return_value = mock_response
        
        result = extract_categorical_options_from_instruction("Rate as poor, fair, good, or excellent")
        
        self.assertEqual(result, ["Poor", "Fair", "Good", "Excellent"])

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_numeric_conversion(self, mock_context):
        """Test conversion of numeric ranges to categorical options."""
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = '{"options": ["1", "2", "3", "4", "5"]}'
        mock_client.get_chat_completions_result.return_value = mock_response
        
        result = extract_categorical_options_from_instruction("Rate from 1 to 5")
        
        self.assertEqual(result, ["1", "2", "3", "4", "5"])

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_fallback_on_error(self, mock_context):
        """Test fallback to Pass/Fail when LLM call fails."""
        mock_context.get_context.side_effect = Exception("Connection failed")
        
        result = extract_categorical_options_from_instruction("Some instruction")
        
        self.assertEqual(result, ["Pass", "Fail"])

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_invalid_json(self, mock_context):
        """Test fallback when LLM returns invalid JSON."""
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = 'invalid json'
        mock_client.get_chat_completions_result.return_value = mock_response
        
        result = extract_categorical_options_from_instruction("Some instruction")
        
        self.assertEqual(result, ["Pass", "Fail"])

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_invalid_options(self, mock_context):
        """Test fallback when LLM returns invalid options."""
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = '{"options": ["OnlyOne"]}'  # Only one option
        mock_client.get_chat_completions_result.return_value = mock_response
        
        result = extract_categorical_options_from_instruction("Some instruction")
        
        self.assertEqual(result, ["Pass", "Fail"])

    @patch('server.utils.schema_analysis.context')
    def test_extract_categorical_options_no_output(self, mock_context):
        """Test fallback when LLM returns no output."""
        mock_client = Mock()
        mock_context.get_context.return_value.build_managed_rag_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.output = None
        mock_client.get_chat_completions_result.return_value = mock_response
        
        result = extract_categorical_options_from_instruction("Some instruction")
        
        self.assertEqual(result, ["Pass", "Fail"])

    def test_is_binary_categorical_options_binary(self):
        """Test binary detection with 2 options."""
        self.assertTrue(is_binary_categorical_options(["Pass", "Fail"]))
        self.assertTrue(is_binary_categorical_options(["Yes", "No"]))

    def test_is_binary_categorical_options_non_binary(self):
        """Test binary detection with non-binary options."""
        self.assertFalse(is_binary_categorical_options(["Poor", "Fair", "Good", "Excellent"]))
        self.assertFalse(is_binary_categorical_options(["1", "2", "3", "4", "5"]))
        self.assertFalse(is_binary_categorical_options(["Single"]))  # Only one option
        self.assertFalse(is_binary_categorical_options([]))  # Empty list


if __name__ == '__main__':
    unittest.main()