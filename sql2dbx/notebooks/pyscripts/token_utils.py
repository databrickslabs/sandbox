from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Tuple, Type

import tiktoken


class TokenizerType(str, Enum):
    """Enum representing different tokenizer types"""
    OPENAI = "openai"
    CLAUDE = "claude"


class BaseTokenCounter(ABC):
    """Abstract base class for token counters"""

    @abstractmethod
    def count_tokens(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        pass


class OpenAITokenCounter(BaseTokenCounter):
    """Token counter for OpenAI models using tiktoken"""

    def __init__(self, token_encoding_name: str = "o200k_base"):
        """Initialize the TokenCounter with a specified token encoding."""
        self.encoding = tiktoken.get_encoding(token_encoding_name)
        self.token_encoding_name = token_encoding_name

    def count_tokens(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        return len(self.encoding.encode(string))


class ClaudeTokenCounter(BaseTokenCounter):
    """Token counter for Claude models based on character to token ratio"""

    def __init__(self, model: str = "claude"):
        """
        Initialize the Claude token counter.

        Args:
            model (str): The Claude model name (currently not used as the ratio
                        appears to be the same across Claude models, but included
                        for future compatibility)
        """
        self.model = model

    def count_tokens(self, string: str) -> int:
        """
        Estimate the number of tokens in the given text for Claude models.

        This estimation is based on Anthropic's documentation, which states that
        approximately 200K tokens correspond to 680K Unicode characters. This implies
        an average of about 3.4 characters per token for Claude models.

        Reference:
        - https://docs.anthropic.com/en/docs/about-claude/models/all-models

        Args:
            string (str): The input text for which to estimate the token count.

        Returns:
            int: The estimated number of tokens in the input text.
        """
        CLAUDE_CHAR_TO_TOKEN_RATIO = 3.4  # Average characters per token for Claude models
        char_count = len(string)
        estimated_tokens = char_count / CLAUDE_CHAR_TO_TOKEN_RATIO
        return int(estimated_tokens)


# Dictionary mapping tokenizer types to their counter classes
TOKEN_COUNTER_CLASSES: Dict[TokenizerType, Type[BaseTokenCounter]] = {
    TokenizerType.OPENAI: OpenAITokenCounter,
    TokenizerType.CLAUDE: ClaudeTokenCounter,
}


def get_token_counter(tokenizer_type: str = "claude", model: str = "claude") -> BaseTokenCounter:
    """
    Factory function to get the appropriate token counter for the specified tokenizer type.

    Args:
        tokenizer_type (str): Type of tokenizer to use ('openai' or 'claude')
        model (str): Model name or encoding to use (for OpenAI this is the encoding name,
                     for Claude this is currently not used but reserved for future compatibility)

    Returns:
        BaseTokenCounter: An instance of the appropriate token counter
    """
    try:
        tokenizer_enum = TokenizerType(tokenizer_type.lower())
        if tokenizer_enum == TokenizerType.CLAUDE:
            return ClaudeTokenCounter()  # model parameter is ignored for Claude currently
        counter_class = TOKEN_COUNTER_CLASSES[tokenizer_enum]
        return counter_class(model)
    except (KeyError, ValueError):
        raise ValueError(f"Unsupported tokenizer type: {tokenizer_type}. "
                         f"Supported types are: {', '.join([t.value for t in TokenizerType])}")


def determine_tokenizer_from_endpoint(endpoint_name: str) -> Tuple[str, str]:
    """
    Determine the tokenizer type and model based on endpoint name.

    Args:
        endpoint_name (str): The endpoint name to determine which tokenizer to use.
                           If 'claude' is in the name, Claude tokenizer is used,
                           otherwise OpenAI tokenizer is used.

    Returns:
        Tuple[str, str]: A tuple containing (tokenizer_type, model)
    """
    if 'claude' in endpoint_name.lower():
        return 'claude', 'claude'
    else:
        return 'openai', 'o200k_base'


def get_token_counter_from_endpoint(endpoint_name: str) -> BaseTokenCounter:
    """
    Get a token counter based on the endpoint name.

    Args:
        endpoint_name (str): The endpoint name to determine which tokenizer to use.
                           If 'claude' is in the name, Claude tokenizer is used,
                           otherwise OpenAI tokenizer is used.

    Returns:
        BaseTokenCounter: An instance of the appropriate token counter
    """
    tokenizer_type, model = determine_tokenizer_from_endpoint(endpoint_name)
    return get_token_counter(tokenizer_type, model)
