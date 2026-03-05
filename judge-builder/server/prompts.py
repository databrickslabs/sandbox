"""Shared prompt templates for judges and optimizers."""

# Default prompt template for custom prompt judges
DEFAULT_JUDGE_PROMPT_TEMPLATE = """You will look at the request and response and determine if they satisfy the evaluation criteria.
Evaluation criteria: {system_instructions}
<request>{{{{request}}}}</request>
<response>{{{{response}}}}</response>

You must choose one of the following categories.
[[pass]]: The response satisfies the evaluation criteria
[[fail]]: The response does not satisfy the evaluation criteria"""

OPTIMIZED_JUDGE_PROMPT_TEMPLATE = """{system_instructions}
<request>{{{{request}}}}</request>
<response>{{{{response}}}}</response>

You must choose one of the following categories.
[[pass]]: The response satisfies the evaluation criteria
[[fail]]: The response does not satisfy the evaluation criteria"""
