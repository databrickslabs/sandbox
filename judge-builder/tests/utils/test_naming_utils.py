"""Unit tests for naming utilities."""

import unittest
from unittest import TestCase

from server.utils.naming_utils import (
    create_dataset_table_name,
    create_scorer_name,
    create_session_name,
    get_short_id,
    sanitize_judge_name,
)


class TestNamingUtils(TestCase):
    """Test cases for naming utility functions."""

    def test_get_short_id_default_length(self):
        """Test get_short_id with default length."""
        full_id = 'abcdef12-3456-7890-abcd-ef1234567890'
        result = get_short_id(full_id)
        self.assertEqual(result, 'abcdef12')
        self.assertEqual(len(result), 8)

    def test_get_short_id_custom_length(self):
        """Test get_short_id with custom length."""
        full_id = 'test-id-123456'
        result = get_short_id(full_id, length=4)
        self.assertEqual(result, 'test')
        self.assertEqual(len(result), 4)

    def test_get_short_id_empty_string(self):
        """Test get_short_id with empty string."""
        result = get_short_id('')
        self.assertEqual(result, '')

    def test_get_short_id_shorter_than_requested(self):
        """Test get_short_id when input is shorter than requested length."""
        short_id = 'abc'
        result = get_short_id(short_id, length=10)
        self.assertEqual(result, 'abc')

    def test_sanitize_judge_name_basic(self):
        """Test basic judge name sanitization."""
        test_cases = [
            ('Quality Judge', 'quality_judge'),
            ('Multi-Word Judge Name!', 'multi_word_judge_name'),
            ('  Spaced  Out  ', 'spaced_out'),
            ('lowercase', 'lowercase'),
            ('UPPERCASE', 'uppercase'),
            ('Numbers123', 'numbers123'),
        ]
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = sanitize_judge_name(input_name)
                self.assertEqual(result, expected)

    def test_sanitize_judge_name_special_characters(self):
        """Test judge name sanitization with special characters."""
        test_cases = [
            ('Judge@#$%Name', 'judge_name'),
            ('Test&Judge*Name', 'test_judge_name'),
            ('Judge(with)brackets', 'judge_with_brackets'),
            ('Judge/slash\\backslash', 'judge_slash_backslash'),
            ('Judge.with.dots', 'judge_with_dots'),
        ]
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = sanitize_judge_name(input_name)
                self.assertEqual(result, expected)

    def test_sanitize_judge_name_multiple_underscores(self):
        """Test judge name sanitization collapses multiple underscores."""
        test_cases = [
            ('Multiple___Underscores', 'multiple_underscores'),
            ('___Leading_Underscores', 'leading_underscores'),
            ('Trailing_Underscores___', 'trailing_underscores'),
            ('___Both___Sides___', 'both_sides'),
            ('A____B____C', 'a_b_c'),
        ]
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = sanitize_judge_name(input_name)
                self.assertEqual(result, expected)

    def test_sanitize_judge_name_edge_cases(self):
        """Test judge name sanitization edge cases."""
        test_cases = [
            ('', ''),
            ('   ', ''),
            ('___', ''),
            ('123', '123'),
            ('_a_', 'a'),
            ('a', 'a'),
        ]
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = sanitize_judge_name(input_name)
                self.assertEqual(result, expected)

    def test_create_scorer_name(self):
        """Test scorer name creation."""
        test_cases = [
            ('Quality Judge', 1, 'v1_instruction_judge_quality_judge'),
            ('Multi-Word Name', 2, 'v2_instruction_judge_multi_word_name'),
            ('Test@Judge#123', 10, 'v10_instruction_judge_test_judge_123'),
            ('', 1, 'v1_instruction_judge_'),
        ]
        for judge_name, version, expected in test_cases:
            with self.subTest(judge_name=judge_name, version=version):
                result = create_scorer_name(judge_name, version)
                self.assertEqual(result, expected)

    def test_create_session_name(self):
        """Test session name creation."""
        test_cases = [
            (
                'Quality Judge',
                'abcd1234-5678-90ab-cdef-123456789012',
                'quality_judge_abcd1234_labeling',
            ),
            (
                'Multi Word',
                'test-id-456',
                'multi_word_test-id-_labeling',
            ),  # get_short_id preserves hyphens
            ('Test@Judge', 'short', 'test_judge_short_labeling'),
        ]
        for judge_name, judge_id, expected in test_cases:
            with self.subTest(judge_name=judge_name, judge_id=judge_id):
                result = create_session_name(judge_name, judge_id)
                self.assertEqual(result, expected)

    def test_create_dataset_table_name(self):
        """Test dataset table name creation."""
        test_cases = [
            (
                'Quality Judge',
                'abcd1234-5678-90ab-cdef-123456789012',
                'judge_quality_judge_abcd1234_examples',
            ),
            (
                'Multi Word',
                'test-id-456',
                'judge_multi_word_test-id-_examples',
            ),  # get_short_id preserves hyphens
            ('Test@Judge', 'short', 'judge_test_judge_short_examples'),
        ]
        for judge_name, judge_id, expected in test_cases:
            with self.subTest(judge_name=judge_name, judge_id=judge_id):
                result = create_dataset_table_name(judge_name, judge_id)
                self.assertEqual(result, expected)

    def test_create_session_name_uses_sanitize_judge_name(self):
        """Test that create_session_name properly sanitizes judge names."""
        judge_name = 'Test@Judge#With$Special%Chars'
        judge_id = 'test123'
        result = create_session_name(judge_name, judge_id)

        # Should use sanitized version of the judge name
        expected = 'test_judge_with_special_chars_test123_labeling'
        self.assertEqual(result, expected)

    def test_create_dataset_table_name_uses_sanitize_judge_name(self):
        """Test that create_dataset_table_name properly sanitizes judge names."""
        judge_name = 'Complex@Judge#Name!'
        judge_id = 'abc456'
        result = create_dataset_table_name(judge_name, judge_id)

        # Should use sanitized version of the judge name
        expected = 'judge_complex_judge_name_abc456_examples'
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
