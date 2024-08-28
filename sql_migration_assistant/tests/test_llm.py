import unittest
from unittest.mock import patch, MagicMock
from app.llm import LLMCalls


class TestLLMCalls(unittest.TestCase):

    @patch('app.llm.OpenAI')
    def setUp(self, MockOpenAI):
        """
        Set up the test environment before each test method.
        Mocks the OpenAI client and initializes the LLMCalls object with mock dependencies.
        """
        # Create a mock client instance
        self.mock_client = MagicMock()
        # Ensure the OpenAI client constructor returns the mock client
        MockOpenAI.return_value = self.mock_client
        # Initialize the LLMCalls instance with dummy parameters
        self.llm = LLMCalls(databricks_host="dummy_host", databricks_token="dummy_token", model_name="dummy_model",
                            max_tokens=100)

    def test_call_llm(self):
        """
        Test the call_llm method of the LLMCalls class.
        Verifies that the method correctly calls the OpenAI client and returns the expected response.
        """
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        self.mock_client.chat.completions.create.return_value = mock_response

        # Test the call_llm method
        messages = [{"role": "user", "content": "Hello"}]
        response = self.llm.call_llm(messages)

        # Verify that the OpenAI client was called with the correct parameters
        self.mock_client.chat.completions.create.assert_called_once_with(messages=messages, model="dummy_model",
                                                                         max_tokens=100)
        # Check that the response matches the expected value
        self.assertEqual(response, "Test response")

    def test_convert_chat_to_llm_input(self):
        """
        Test the convert_chat_to_llm_input method to ensure it correctly formats the chat history.
        """
        system_prompt = "You are a helpful assistant."
        chat = [("Hello", "Hi there!"), ("How are you?", "I'm good, thank you!")]
        expected_output = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm good, thank you!"}
        ]

        result = self.llm.convert_chat_to_llm_input(system_prompt, chat)
        # Assert that the formatted messages are as expected
        self.assertEqual(result, expected_output)

    # Test the LLM functions for translating code, chatting, and determining intent
    @patch.object(LLMCalls, 'call_llm', return_value="Final answer:\nTranslated code")
    def test_llm_translate(self, mock_call_llm):
        system_prompt = "Translate this code"
        input_code = "SELECT * FROM table"

        response = self.llm.llm_translate(system_prompt, input_code)
        self.assertEqual(response, "Translated code")

    @patch.object(LLMCalls, 'call_llm', return_value="Chat response")
    def test_llm_chat(self, mock_call_llm):
        system_prompt = "You are a helpful assistant."
        query = "What is the weather today?"
        chat_history = [("Hello", "Hi there!")]

        response = self.llm.llm_chat(system_prompt, query, chat_history)
        self.assertEqual(response, "Chat response")

    @patch.object(LLMCalls, 'call_llm', return_value="Intent response")
    def test_llm_intent(self, mock_call_llm):
        system_prompt = "Determine the intent of this code"
        input_code = "SELECT * FROM table"

        response = self.llm.llm_intent(system_prompt, input_code)
        self.assertEqual(response, "Intent response")


if __name__ == '__main__':
    unittest.main()
