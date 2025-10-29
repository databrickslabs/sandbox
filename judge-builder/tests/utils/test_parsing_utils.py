"""Unit tests for parsing utilities."""

import json
import unittest
from unittest import TestCase

from server.utils.parsing_utils import extract_text_from_data


class TestParsingUtils(TestCase):
    """Test cases for parsing utility functions."""

    def test_extract_text_from_data_none_input(self):
        """Test extract_text_from_data with None input."""
        result = extract_text_from_data(None, 'request')
        self.assertEqual(result, '')

    def test_extract_text_from_data_empty_string(self):
        """Test extract_text_from_data with empty string."""
        result = extract_text_from_data('', 'request')
        self.assertEqual(result, '')

    def test_extract_text_from_data_plain_string(self):
        """Test extract_text_from_data with plain string."""
        test_cases = [
            ('Hello world', 'Hello world'),
            ('Simple request text', 'Simple request text'),
            ('Response with numbers 123', 'Response with numbers 123'),
        ]
        for input_text, expected in test_cases:
            for field_type in ['request', 'response']:
                with self.subTest(input_text=input_text, field_type=field_type):
                    result = extract_text_from_data(input_text, field_type)
                    self.assertEqual(result, expected)

    def test_extract_text_from_data_json_string_request(self):
        """Test extract_text_from_data with JSON string for request field."""
        test_cases = [
            ('{"request": "What is AI?"}', 'What is AI?'),
            ('{"inputs": "Tell me about ML"}', 'Tell me about ML'),
            ('{"input": "Explain Python"}', 'Explain Python'),
            ('{"prompt": "Write a story"}', 'Write a story'),
        ]
        for json_str, expected in test_cases:
            with self.subTest(json_str=json_str):
                result = extract_text_from_data(json_str, 'request')
                self.assertEqual(result, expected)

    def test_extract_text_from_data_json_string_response(self):
        """Test extract_text_from_data with JSON string for response field."""
        test_cases = [
            ('{"response": "AI is artificial intelligence"}', 'AI is artificial intelligence'),
            ('{"outputs": "ML is machine learning"}', 'ML is machine learning'),
            ('{"output": "Python is a programming language"}', 'Python is a programming language'),
            ('{"content": "Once upon a time..."}', 'Once upon a time...'),
            ('{"text": "Here is the answer"}', 'Here is the answer'),
        ]
        for json_str, expected in test_cases:
            with self.subTest(json_str=json_str):
                result = extract_text_from_data(json_str, 'response')
                self.assertEqual(result, expected)

    def test_extract_text_from_data_invalid_json_string(self):
        """Test extract_text_from_data with invalid JSON string."""
        invalid_json_cases = [
            '{"invalid": json}',  # Missing quotes
            '{"unclosed": "string',  # Unclosed string
            'not json at all',  # Plain text that's not JSON
            '{broken json',  # Malformed JSON
        ]
        for invalid_json in invalid_json_cases:
            with self.subTest(invalid_json=invalid_json):
                result = extract_text_from_data(invalid_json, 'request')
                self.assertEqual(result, invalid_json)  # Should return original string

    def test_extract_text_from_data_dict_request(self):
        """Test extract_text_from_data with dict for request field."""
        test_cases = [
            ({'request': 'What is AI?'}, 'What is AI?'),
            ({'inputs': 'Tell me about ML'}, 'Tell me about ML'),
            ({'input': 'Explain Python'}, 'Explain Python'),
            ({'prompt': 'Write a story'}, 'Write a story'),
            ({'request': {'nested': 'data'}}, '{"nested": "data"}'),  # Dict value becomes JSON
            (
                {'inputs': ['list', 'of', 'items']},
                '["list", "of", "items"]',
            ),  # List value becomes JSON
        ]
        for input_dict, expected in test_cases:
            with self.subTest(input_dict=input_dict):
                result = extract_text_from_data(input_dict, 'request')
                self.assertEqual(result, expected)

    def test_extract_text_from_data_dict_response(self):
        """Test extract_text_from_data with dict for response field."""
        test_cases = [
            ({'response': 'AI is artificial intelligence'}, 'AI is artificial intelligence'),
            ({'outputs': 'ML is machine learning'}, 'ML is machine learning'),
            ({'output': 'Python is a programming language'}, 'Python is a programming language'),
            ({'content': 'Once upon a time...'}, 'Once upon a time...'),
            ({'text': 'Here is the answer'}, 'Here is the answer'),
            (
                {'response': {'structured': 'data'}},
                '{"structured": "data"}',
            ),  # Dict value becomes JSON
            ({'outputs': [1, 2, 3]}, '[1, 2, 3]'),  # List value becomes JSON
        ]
        for input_dict, expected in test_cases:
            with self.subTest(input_dict=input_dict):
                result = extract_text_from_data(input_dict, 'response')
                self.assertEqual(result, expected)

    def test_extract_text_from_data_dict_no_matching_keys(self):
        """Test extract_text_from_data with dict that has no matching keys."""
        test_cases = [
            ({'other': 'data', 'random': 'fields'}, 'request'),
            ({'unrelated': 'content', 'misc': 'info'}, 'response'),
        ]
        for input_dict, field_type in test_cases:
            with self.subTest(input_dict=input_dict, field_type=field_type):
                result = extract_text_from_data(input_dict, field_type)
                expected = json.dumps(input_dict)
                self.assertEqual(result, expected)

    def test_extract_text_from_data_key_priority_request(self):
        """Test extract_text_from_data key priority for request field."""
        # Should prefer 'request' over 'inputs' over 'input' over 'prompt'
        data_with_multiple_keys = {
            'prompt': 'lowest priority',
            'input': 'medium-low priority',
            'inputs': 'medium-high priority',
            'request': 'highest priority',
        }
        result = extract_text_from_data(data_with_multiple_keys, 'request')
        self.assertEqual(result, 'highest priority')

    def test_extract_text_from_data_key_priority_response(self):
        """Test extract_text_from_data key priority for response field."""
        # Should prefer 'response' over 'outputs' over 'output' over 'content' over 'text'
        data_with_multiple_keys = {
            'text': 'lowest priority',
            'content': 'medium-low priority',
            'output': 'medium priority',
            'outputs': 'medium-high priority',
            'response': 'highest priority',
        }
        result = extract_text_from_data(data_with_multiple_keys, 'response')
        self.assertEqual(result, 'highest priority')

    def test_extract_text_from_data_other_types(self):
        """Test extract_text_from_data with other data types."""
        test_cases = [
            (123, '123'),
            (45.67, '45.67'),
            (True, 'True'),
            (False, 'False'),
            ([1, 2, 3], '[1, 2, 3]'),
        ]
        for input_data, expected in test_cases:
            for field_type in ['request', 'response']:
                with self.subTest(input_data=input_data, field_type=field_type):
                    result = extract_text_from_data(input_data, field_type)
                    self.assertEqual(result, expected)

    def test_extract_text_from_data_json_string_with_complex_data(self):
        """Test extract_text_from_data with JSON string containing complex data."""
        complex_request = {
            'request': {
                'question': 'What is AI?',
                'context': ['machine learning', 'neural networks'],
                'metadata': {'source': 'test'},
            }
        }
        json_str = json.dumps(complex_request)
        result = extract_text_from_data(json_str, 'request')

        # Should extract the 'request' value and convert dict to JSON string
        expected = json.dumps(
            {
                'question': 'What is AI?',
                'context': ['machine learning', 'neural networks'],
                'metadata': {'source': 'test'},
            }
        )
        self.assertEqual(result, expected)

    def test_extract_text_from_data_empty_dict(self):
        """Test extract_text_from_data with empty dict."""
        result = extract_text_from_data({}, 'request')
        self.assertEqual(result, '{}')

    def test_extract_text_from_data_nested_json_parsing(self):
        """Test extract_text_from_data with nested JSON that needs parsing."""
        # JSON string containing another JSON string
        nested_json = '{"request": "{\\"nested\\": \\"json\\", \\"value\\": 123}"}'
        result = extract_text_from_data(nested_json, 'request')
        self.assertEqual(result, '{"nested": "json", "value": 123}')


from unittest.mock import Mock, patch

import pytest
from mlflow.entities import Assessment, AssessmentSource

from server.utils.parsing_utils import (
    assessment_has_error,
    extract_request_from_trace,
    extract_response_from_trace,
    get_human_feedback_from_trace,
    get_scorer_feedback_from_trace,
)


def create_mock_trace(
    request_data=None,
    response_data=None,
    request_preview='preview request',
    response_preview='preview response',
):
    """Helper to create mock trace objects for testing."""
    mock_trace = type('MockTrace', (), {})()
    mock_trace.data = type('MockData', (), {})()
    if request_data is not None:
        mock_trace.data.request = request_data
    if response_data is not None:
        mock_trace.data.response = response_data
    mock_trace.info = type('MockInfo', (), {})()
    mock_trace.info.request_preview = request_preview
    mock_trace.info.response_preview = response_preview
    return mock_trace


@pytest.mark.parametrize(
    'request_data, expected',
    [
        ({'input': 'test request'}, 'test request'),
        ('plain string request', 'plain string request'),
        ('{"request": "json request data"}', 'json request data'),
    ],
)
def test_extract_request_from_trace_with_data(request_data, expected):
    """Test extract_request_from_trace when trace.data.request exists."""
    mock_trace = create_mock_trace(request_data=request_data)
    result = extract_request_from_trace(mock_trace)
    assert result == expected


@pytest.mark.parametrize(
    'response_data, expected',
    [
        ({'output': 'test response'}, 'test response'),
        ('plain string response', 'plain string response'),
        ('{"response": "json response data"}', 'json response data'),
    ],
)
def test_extract_response_from_trace_with_data(response_data, expected):
    """Test extract_response_from_trace when trace.data.response exists."""
    mock_trace = create_mock_trace(response_data=response_data)
    result = extract_response_from_trace(mock_trace)
    assert result == expected


def test_extract_request_from_trace_fallback_to_preview():
    """Test extract_request_from_trace falls back to request_preview."""
    mock_trace = create_mock_trace(request_preview='fallback request')
    # No request data set, should fall back to preview
    result = extract_request_from_trace(mock_trace)
    assert result == 'fallback request'


def test_extract_response_from_trace_fallback_to_preview():
    """Test extract_response_from_trace falls back to response_preview."""
    mock_trace = create_mock_trace(response_preview='fallback response')
    # No response data set, should fall back to preview
    result = extract_response_from_trace(mock_trace)
    assert result == 'fallback response'


# Tests for new parsing utility functions

@pytest.fixture
def mock_trace_with_assessments():
    """Create a mock trace object with assessments."""
    trace = Mock()
    trace.info = Mock()
    trace.info.trace_id = 'trace-123'
    trace.info.assessments = []
    return trace


@pytest.fixture
def mock_assessment():
    """Create a mock assessment object."""
    assessment = Mock()
    assessment.name = 'test_judge'
    assessment.source = Mock()
    assessment.source.source_type = 'HUMAN'
    assessment.metadata = {'version': '1'}
    assessment.error = None
    assessment.feedback = Mock()
    assessment.feedback.value = 'Pass'
    return assessment


def test_get_human_feedback_no_assessments(mock_trace_with_assessments):
    """Test get_human_feedback_from_trace with no assessments."""
    mock_trace_with_assessments.info.assessments = None

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result is None


def test_get_human_feedback_empty_assessments(mock_trace_with_assessments):
    """Test get_human_feedback_from_trace with empty assessments."""
    mock_trace_with_assessments.info.assessments = []

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result is None


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_human_feedback_found(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_human_feedback_from_trace when human feedback is found."""
    mock_sanitize.return_value = 'test_judge'
    mock_assessment.source.source_type = 'HUMAN'
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result == mock_assessment
    mock_sanitize.assert_called_once_with('Test Judge')


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_human_feedback_not_found_wrong_source(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_human_feedback_from_trace when assessment has wrong source type."""
    mock_sanitize.return_value = 'test_judge'
    mock_assessment.source.source_type = 'LLM_JUDGE'
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result is None


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_human_feedback_not_found_wrong_name(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_human_feedback_from_trace when assessment has wrong name."""
    mock_sanitize.return_value = 'different_judge'
    mock_assessment.source.source_type = 'HUMAN'
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result is None


def test_get_scorer_feedback_no_assessments(mock_trace_with_assessments):
    """Test get_scorer_feedback_from_trace with no assessments."""
    mock_trace_with_assessments.info.assessments = None

    result = get_scorer_feedback_from_trace('Test Judge', 1, mock_trace_with_assessments)

    assert result is None


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_scorer_feedback_found(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_scorer_feedback_from_trace when scorer feedback is found."""
    mock_sanitize.return_value = 'test_judge'
    mock_assessment.source.source_type = 'LLM_JUDGE'
    mock_assessment.metadata = {'version': '1'}
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_scorer_feedback_from_trace('Test Judge', 1, mock_trace_with_assessments)

    assert result == mock_assessment
    mock_sanitize.assert_called_once_with('Test Judge')


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_scorer_feedback_wrong_version(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_scorer_feedback_from_trace with wrong version."""
    mock_sanitize.return_value = 'test_judge'
    mock_assessment.source.source_type = 'LLM_JUDGE'
    mock_assessment.metadata = {'version': '2'}
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_scorer_feedback_from_trace('Test Judge', 1, mock_trace_with_assessments)

    assert result is None


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_scorer_feedback_no_metadata(mock_sanitize, mock_trace_with_assessments, mock_assessment):
    """Test get_scorer_feedback_from_trace with no metadata."""
    mock_sanitize.return_value = 'test_judge'
    mock_assessment.source.source_type = 'LLM_JUDGE'
    mock_assessment.metadata = None
    mock_trace_with_assessments.info.assessments = [mock_assessment]

    result = get_scorer_feedback_from_trace('Test Judge', 1, mock_trace_with_assessments)

    assert result is None


def test_assessment_has_error_no_error(mock_assessment):
    """Test assessment_has_error with no error."""
    mock_assessment.error = None

    result = assessment_has_error(mock_assessment)

    assert result is False


def test_assessment_has_error_with_error(mock_assessment):
    """Test assessment_has_error with error present."""
    mock_assessment.error = 'Some error'

    result = assessment_has_error(mock_assessment)

    assert result is True


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_human_feedback_multiple_assessments(mock_sanitize, mock_trace_with_assessments):
    """Test get_human_feedback_from_trace with multiple assessments."""
    mock_sanitize.return_value = 'test_judge'

    # Create multiple assessments
    assessment1 = Mock(spec=Assessment)
    assessment1.name = 'other_judge'
    assessment1.source = Mock(spec=AssessmentSource)
    assessment1.source.source_type = 'HUMAN'

    assessment2 = Mock(spec=Assessment)
    assessment2.name = 'test_judge'
    assessment2.source = Mock(spec=AssessmentSource)
    assessment2.source.source_type = 'LLM_JUDGE'

    assessment3 = Mock(spec=Assessment)
    assessment3.name = 'test_judge'
    assessment3.source = Mock(spec=AssessmentSource)
    assessment3.source.source_type = 'HUMAN'

    mock_trace_with_assessments.info.assessments = [assessment1, assessment2, assessment3]

    result = get_human_feedback_from_trace('Test Judge', mock_trace_with_assessments)

    assert result == assessment3  # Should return the correct matching assessment


@patch('server.utils.parsing_utils.sanitize_judge_name')
def test_get_scorer_feedback_multiple_versions(mock_sanitize, mock_trace_with_assessments):
    """Test get_scorer_feedback_from_trace with multiple versions."""
    mock_sanitize.return_value = 'test_judge'

    # Create assessments with different versions
    assessment1 = Mock(spec=Assessment)
    assessment1.name = 'test_judge'
    assessment1.source = Mock(spec=AssessmentSource)
    assessment1.source.source_type = 'LLM_JUDGE'
    assessment1.metadata = {'version': '1'}

    assessment2 = Mock(spec=Assessment)
    assessment2.name = 'test_judge'
    assessment2.source = Mock(spec=AssessmentSource)
    assessment2.source.source_type = 'LLM_JUDGE'
    assessment2.metadata = {'version': '2'}

    mock_trace_with_assessments.info.assessments = [assessment1, assessment2]

    result = get_scorer_feedback_from_trace('Test Judge', 2, mock_trace_with_assessments)

    assert result == assessment2  # Should return version 2


if __name__ == '__main__':
    unittest.main()
