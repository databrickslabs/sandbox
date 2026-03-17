"""Built-in MLflow 3 scorers for agent evaluation.

These ``@scorer`` functions are designed for use with ``mlflow.genai.evaluate()``
and the ``app_predict_fn()`` bridge.

Requires ``mlflow>=3.0.0``.  Import will raise ``ImportError`` with a clear
message when MLflow 3 is not installed.

Usage::

    from dbx_agent_app.bridge.scorers import response_not_empty, response_contains
    import mlflow

    results = mlflow.genai.evaluate(
        data=[{"inputs": {"messages": [{"role": "user", "content": "Hello"}]}}],
        predict_fn=predict,
        scorers=[response_not_empty, response_contains],
    )
"""

from __future__ import annotations

try:
    from mlflow.genai.scorers import scorer
    from mlflow.entities import Feedback
except ImportError as e:
    raise ImportError(
        "Built-in scorers require mlflow>=3.0.0. "
        "Install with: pip install 'dbx-agent-app[mlflow]'"
    ) from e


@scorer
def response_not_empty(*, outputs: dict) -> bool:
    """Check that the agent returned a non-empty response."""
    response = outputs.get("response", "")
    return bool(response and response.strip())


@scorer
def latency_under(*, outputs: dict, expectations: dict) -> Feedback:
    """Check response latency is under a threshold (ms).

    Set ``expectations={"max_latency_ms": 5000}`` in your eval data.
    """
    threshold = expectations.get("max_latency_ms", 5000)
    actual = outputs.get("latency_ms", 0)
    return Feedback(
        value=actual <= threshold,
        rationale=f"Latency {actual}ms vs threshold {threshold}ms",
    )


@scorer
def tool_was_called(*, outputs: dict, expectations: dict) -> Feedback:
    """Check that an expected tool was invoked.

    Set ``expectations={"expected_tool": "search_transcripts"}`` in your eval data.
    The agent's output should include a ``tools_used`` list.
    """
    expected_tool = expectations.get("expected_tool")
    tools_used = outputs.get("tools_used", [])
    found = expected_tool in tools_used if expected_tool else True
    return Feedback(
        value=found,
        rationale=f"Expected tool '{expected_tool}', tools used: {tools_used}",
    )


@scorer
def response_contains(*, outputs: dict, expectations: dict) -> Feedback:
    """Check that the response contains expected substring(s).

    Set ``expectations={"must_contain": ["keyword1", "keyword2"]}`` or
    ``expectations={"must_contain": "keyword"}`` in your eval data.
    """
    response = outputs.get("response", "")
    must_contain = expectations.get("must_contain", [])
    if isinstance(must_contain, str):
        must_contain = [must_contain]
    missing = [s for s in must_contain if s.lower() not in response.lower()]
    return Feedback(
        value=len(missing) == 0,
        rationale=f"Missing: {missing}" if missing else "All expected content found",
    )


def make_llm_relevance_scorer(
    model_endpoint: str = "databricks-claude-sonnet-4",
):
    """Create an LLM-as-judge scorer that evaluates response relevance.

    Uses a foundation model endpoint to judge whether the agent's response
    is relevant and helpful given the user's question.

    Args:
        model_endpoint: Databricks serving endpoint name for the judge LLM.

    Returns:
        A ``@scorer`` function for use with ``mlflow.genai.evaluate()``.

    Usage::

        from dbx_agent_app.bridge.scorers import make_llm_relevance_scorer

        llm_relevance = make_llm_relevance_scorer("databricks-claude-sonnet-4")
        results = mlflow.genai.evaluate(
            data=eval_data,
            predict_fn=predict,
            scorers=[llm_relevance],
        )
    """
    from mlflow.genai.judges import is_correct

    @scorer
    def llm_relevance(*, inputs: dict, outputs: dict, expectations: dict) -> Feedback:
        """Judge whether the response is relevant and correct using an LLM."""
        messages = inputs.get("messages", [])
        question = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                question = msg.get("content", "")
                break

        response = outputs.get("response", "")
        context = expectations.get("expected_facts", [])
        if isinstance(context, str):
            context = [context]

        result = is_correct(
            request=question,
            response=response,
            expected_facts=context,
        )
        return result

    llm_relevance.__name__ = f"llm_relevance_{model_endpoint.replace('-', '_')}"
    return llm_relevance
