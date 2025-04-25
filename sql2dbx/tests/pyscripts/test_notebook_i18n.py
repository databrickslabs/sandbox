import unittest
from enum import Enum

from notebooks.pyscripts.notebook_i18n import (MessageKey,
                                               get_language_messages,
                                               get_supported_languages)


class TestI18n(unittest.TestCase):
    """Test cases for the i18n module."""

    def test_message_key_enum(self):
        """Test that MessageKey is correctly defined as an Enum."""
        self.assertTrue(issubclass(MessageKey, Enum))
        self.assertEqual(MessageKey.NOTEBOOK_DESCRIPTION.value, "notebook_description")
        self.assertEqual(MessageKey.SOURCE_SCRIPT.value, "source_script")
        self.assertEqual(MessageKey.SYNTAX_CHECK_RESULTS.value, "syntax_check_results")
        self.assertEqual(MessageKey.ERRORS_FROM_CHECKS.value, "errors_from_checks")
        self.assertEqual(MessageKey.PYTHON_SYNTAX_ERRORS.value, "python_syntax_errors")
        self.assertEqual(MessageKey.SPARK_SQL_SYNTAX_ERRORS.value, "spark_sql_syntax_errors")
        self.assertEqual(MessageKey.NO_ERRORS_DETECTED.value, "no_errors_detected")
        self.assertEqual(MessageKey.REVIEW_CODE.value, "review_code")

    def test_supported_languages(self):
        """Test that get_supported_languages returns the expected languages."""
        languages = get_supported_languages()
        expected_languages = [
            "English", "Japanese", "Chinese", "French", "German",
            "Italian", "Korean", "Portuguese", "Spanish"
        ]
        self.assertEqual(sorted(languages), sorted(expected_languages))
        self.assertEqual(len(languages), 9)  # Should be 9 languages supported

    def test_get_language_messages_returns_dict(self):
        """Test that get_language_messages returns a dictionary."""
        for lang in get_supported_languages():
            messages = get_language_messages(lang)
            self.assertIsInstance(messages, dict)
            # Check that all MessageKey enum values are in the dictionary
            for key in MessageKey:
                self.assertIn(key, messages)
                self.assertIsInstance(messages[key], str)

    def test_get_language_messages_fallback(self):
        """Test that get_language_messages falls back to English for unsupported languages."""
        en_messages = get_language_messages("English")
        # Test with an unsupported language
        unsupported_messages = get_language_messages("Unsupported")
        self.assertEqual(en_messages, unsupported_messages)

    def test_language_specific_messages(self):
        """Test that each language has the correct specific messages."""
        # Test a sample message from each language
        self.assertEqual(
            get_language_messages("English")[MessageKey.SOURCE_SCRIPT],
            "Source script"
        )
        self.assertEqual(
            get_language_messages("Japanese")[MessageKey.SOURCE_SCRIPT],
            "ソーススクリプト"
        )
        self.assertEqual(
            get_language_messages("Chinese")[MessageKey.SOURCE_SCRIPT],
            "源脚本"
        )
        self.assertEqual(
            get_language_messages("French")[MessageKey.SOURCE_SCRIPT],
            "Script source"
        )
        self.assertEqual(
            get_language_messages("German")[MessageKey.SOURCE_SCRIPT],
            "Quellskript"
        )
        self.assertEqual(
            get_language_messages("Italian")[MessageKey.SOURCE_SCRIPT],
            "Script sorgente"
        )
        self.assertEqual(
            get_language_messages("Korean")[MessageKey.SOURCE_SCRIPT],
            "소스 스크립트"
        )
        self.assertEqual(
            get_language_messages("Portuguese")[MessageKey.SOURCE_SCRIPT],
            "Script fonte"
        )
        self.assertEqual(
            get_language_messages("Spanish")[MessageKey.SOURCE_SCRIPT],
            "Script fuente"
        )

    def test_message_formatting(self):
        """Test that multi-line messages are properly formatted."""
        for lang in get_supported_languages():
            messages = get_language_messages(lang)
            # Checking that the notebook description doesn't have newlines
            # as we're using string concatenation in the definition
            notebook_desc = messages[MessageKey.NOTEBOOK_DESCRIPTION]
            self.assertNotIn("\n", notebook_desc)

            # Check that messages are not empty
            for key in MessageKey:
                self.assertTrue(messages[key], f"Message for {key} in {lang} is empty")


if __name__ == "__main__":
    unittest.main()
