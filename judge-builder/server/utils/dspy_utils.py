import dspy
import logging
from databricks.rag_eval import context, env_vars

from server.utils.constants import VERSION

logger = logging.getLogger(__name__)

# Default alignment model configuration
DEFAULT_ALIGNMENT_MODEL = "gpt-oss-120b"


class AttrDict(dict):
    """A dict that allows attribute-style access (like OpenAI's objects)."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


def to_attrdict(obj):
    """Recursively convert nested dicts/lists to AttrDicts."""
    if isinstance(obj, dict):
        return AttrDict({k: to_attrdict(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [to_attrdict(item) for item in obj]
    else:
        return obj


class AgentEvalLM(dspy.BaseLM):
    def __init__(self, model: str, temperature: float = 1.0):
        super().__init__('databricks/databricks-llama-4-maverick')
        self.model = model
        self.temperature = temperature
        env_vars.RAG_EVAL_EVAL_SESSION_CLIENT_NAME.set(f'judge-builder-v{VERSION}')

    def dump_state(self):
        return {}

    def load_state(self, state):
        pass

    def forward(self, prompt=None, messages=None, **kwargs):
        return self._forward_impl(prompt=prompt, messages=messages, **kwargs)

    @context.eval_context
    def _forward_impl(self, prompt=None, messages=None, **kwargs):
        """Forward pass for the language model.
        Subclasses must implement this method, and the response should be identical to
        [OpenAI response format](https://platform.openai.com/docs/api-reference/responses/object).
        """
        # Get the managed_rag_client from the context
        managed_rag_client = context.get_context().build_managed_rag_client()

        # Convert messages to the format expected by managed_rag_client
        user_prompt = None
        system_prompt = None

        if messages:
            # Extract user and system prompts from messages
            for message in messages:
                if message.get('role') == 'user':
                    user_prompt = message.get('content', '')
                elif message.get('role') == 'system':
                    system_prompt = message.get('content', '')

        # If no user prompt found in messages, use the prompt parameter
        if not user_prompt and prompt:
            user_prompt = prompt

        # Call the managed_rag_client
        response = managed_rag_client.get_chat_completions_result(
            user_prompt=user_prompt, system_prompt=system_prompt, model=self.model, temperature=self.temperature
        )

        # Convert the response to the expected format
        if response.output is not None:
            result_dict = {
                'object': 'chat.completion',
                'model': self.model,
                'usage': {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                },
                'choices': [
                    {
                        'index': 0,
                        'finish_reason': 'stop',
                        'message': {'role': 'assistant', 'content': response.output},
                    }
                ],
                'response_format': 'json_object',
            }
        else:
            result_dict = {
                'object': 'response',
                'error': response.error_message,
                'usage': {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                },
                'response_format': 'json_object',
            }

        # Convert to attrdict-like format (simple dict access)
        return to_attrdict(result_dict)
