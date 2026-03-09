"""
Eval bridge: wrap a Databricks App as a predict_fn for mlflow.genai.evaluate().

The official ``databricks-agents`` package provides ``mlflow.genai.to_predict_fn()``
for Model Serving endpoints, but Databricks Apps aren't model serving endpoints.
This module fills that gap.

Usage::

    from dbx_agent_app.bridge import app_predict_fn

    predict = app_predict_fn("https://my-app.cloud.databricks.com")

    # Use with mlflow.genai.evaluate()
    import mlflow
    results = mlflow.genai.evaluate(
        data=[{"inputs": {"messages": [{"role": "user", "content": "Hello"}]}}],
        predict_fn=predict,
        scorers=[...],
    )

Wire format translation:

    evaluate() calls:  predict_fn(messages=[{"role": "user", "content": "..."}])
    Bridge sends:      POST {app_url}/invocations  {"input": [{"role": "user", "content": "..."}]}
    App returns:       {"output": [{"type": "message", "content": [{"text": "..."}]}]}
    Bridge returns:    {"response": "...", "output": [...]}
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def app_predict_fn(
    app_url: str,
    *,
    token: Optional[str] = None,
    timeout: float = 120.0,
) -> Callable[..., Dict[str, Any]]:
    """
    Create a predict_fn that calls a Databricks App's /invocations endpoint.

    Args:
        app_url: Base URL of the deployed Databricks App (e.g. "https://my-app.cloud.databricks.com").
            Trailing slashes are stripped.
        token: Databricks PAT for authentication. If None, reads from DATABRICKS_TOKEN env var.
        timeout: HTTP timeout in seconds (default: 120).

    Returns:
        A callable ``predict_fn(messages=...) -> dict`` compatible with
        ``mlflow.genai.evaluate()``.

    Raises:
        httpx.HTTPStatusError: If the app returns a non-2xx response.
        ValueError: If no authentication token is available.
    """
    import os

    import httpx

    resolved_token = token or os.environ.get("DATABRICKS_TOKEN")
    if not resolved_token:
        raise ValueError(
            "No auth token provided. Pass token= or set DATABRICKS_TOKEN env var."
        )

    base = app_url.rstrip("/")
    url = f"{base}/invocations"

    headers = {
        "Authorization": f"Bearer {resolved_token}",
        "Content-Type": "application/json",
    }

    client = httpx.Client(timeout=timeout, headers=headers)

    def predict(
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Call the app's /invocations endpoint.

        Accepts either:
            predict(messages=[{"role": "user", "content": "..."}])
            predict(question="...") — auto-wraps as single user message
        """
        if messages is None:
            # Support simple string input (e.g. predict(question="Hello"))
            text = kwargs.get("question") or kwargs.get("input") or kwargs.get("query")
            if text:
                messages = [{"role": "user", "content": str(text)}]
            else:
                raise ValueError(
                    "predict_fn requires 'messages' list or a 'question'/'input'/'query' kwarg"
                )

        # Translate to our wire format
        payload = {"input": messages}

        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract text from our output format
        text_parts = []
        for item in data.get("output", []):
            for content_block in item.get("content", []):
                if "text" in content_block:
                    text_parts.append(content_block["text"])

        return {
            "response": "\n".join(text_parts),
            "output": data.get("output", []),
        }

    return predict
