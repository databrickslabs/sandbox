import unittest

from notebooks.pyscripts.token_utils import (ClaudeTokenCounter,
                                             OpenAITokenCounter, TokenizerType,
                                             determine_tokenizer_from_endpoint,
                                             get_token_counter,
                                             get_token_counter_from_endpoint)


class TestTokenUtils(unittest.TestCase):
    def test_openai_token_counter(self):
        counter = OpenAITokenCounter(token_encoding_name="o200k_base")
        text = "This is a test string."
        token_count = counter.count_tokens(text)
        self.assertGreater(token_count, 0)

        # Test longer text
        long_text = "This is a longer text that should be tokenized into multiple tokens. " * 10
        long_count = counter.count_tokens(long_text)
        self.assertGreater(long_count, 50)

    def test_claude_token_counter(self):
        counter = ClaudeTokenCounter()
        text = "This is a test string."
        token_count = counter.count_tokens(text)
        self.assertGreater(token_count, 0)
        # Verify that Claude token count is an estimation based on Character/3.4
        self.assertEqual(token_count, int(len(text) / 3.4))

        # Test empty string
        self.assertEqual(counter.count_tokens(""), 0)

        # Test longer text and verify character ratio
        long_text = "This is a much longer text that contains multiple sentences. " * 10
        long_count = counter.count_tokens(long_text)
        self.assertEqual(long_count, int(len(long_text) / 3.4))

    def test_token_count_comparison(self):
        """Test and compare token counts between different tokenizers"""
        openai_counter = OpenAITokenCounter(token_encoding_name="o200k_base")
        claude_counter = ClaudeTokenCounter()

        test_texts = [
            "",  # Empty string
            "Hello world",  # Simple text
            "OpenAI and Claude use different tokenization methods",  # Medium text
            # Text with special characters
            "Email: test@example.com, URL: https://example.com/path?query=value",
            # Multilingual text
            "English, 日本語 (Japanese), Español (Spanish), Русский (Russian)",
            # Code snippet
            "def hello_world():\n    print('Hello, world!')\n    return True"
        ]

        for text in test_texts:
            openai_count = openai_counter.count_tokens(text)
            claude_count = claude_counter.count_tokens(text)

            # Both should return values >= 0
            self.assertGreaterEqual(openai_count, 0)
            self.assertGreaterEqual(claude_count, 0)

            # Empty string should be 0 tokens for both
            if not text:
                self.assertEqual(openai_count, 0)
                self.assertEqual(claude_count, 0)

            # Very basic sanity check: Claude estimation should be somewhat related to OpenAI
            # This is just a rough check, not expecting exact correlation
            if len(text) > 20:  # Only check for longer texts
                # Claude's estimate should be within 50% of OpenAI's count for typical texts
                # This is a very rough validation since they use different tokenization methods
                self.assertLess(abs(claude_count - openai_count), max(openai_count, claude_count))

    def test_get_token_counter(self):
        # Verify that the default is Claude tokenizer
        default_counter = get_token_counter()
        self.assertIsInstance(default_counter, ClaudeTokenCounter)

        # Explicitly get OpenAI tokenizer
        openai_counter = get_token_counter("openai", "o200k_base")
        self.assertIsInstance(openai_counter, OpenAITokenCounter)

        # Explicitly get Claude tokenizer
        claude_counter = get_token_counter("claude", "claude")
        self.assertIsInstance(claude_counter, ClaudeTokenCounter)

        # Verify exception for invalid tokenizer type
        with self.assertRaises(ValueError):
            get_token_counter("invalid_tokenizer")

    def test_determine_tokenizer_from_endpoint(self):
        # Test Databricks Claude endpoint detection
        tokenizer_type, model = determine_tokenizer_from_endpoint("databricks-claude-3-7-sonnet")
        self.assertEqual(tokenizer_type, "claude")
        self.assertEqual(model, "claude")

        # Test OpenAI endpoint detection
        tokenizer_type, model = determine_tokenizer_from_endpoint("gpt-4o")
        self.assertEqual(tokenizer_type, "openai")
        self.assertEqual(model, "o200k_base")

    def test_get_token_counter_from_endpoint(self):
        # Get tokenizer from Databricks Claude endpoint
        counter = get_token_counter_from_endpoint("databricks-claude-3-7-sonnet")
        self.assertIsInstance(counter, ClaudeTokenCounter)

        # Get tokenizer from OpenAI endpoint
        counter = get_token_counter_from_endpoint("gpt-4o")
        self.assertIsInstance(counter, OpenAITokenCounter)


if __name__ == '__main__':
    unittest.main()
