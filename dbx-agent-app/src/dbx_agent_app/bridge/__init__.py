"""
Bridge module for interoperability with the official ``databricks-agents`` package.

Provides ``app_predict_fn()`` which wraps a Databricks App's /invocations
endpoint as a ``predict_fn`` compatible with ``mlflow.genai.evaluate()``.

Built-in scorers are available via explicit import::

    from dbx_agent_app.bridge.scorers import response_not_empty, response_contains
"""

from dbx_agent_app.bridge.eval import app_conversation_fn, app_predict_fn

__all__ = ["app_conversation_fn", "app_predict_fn"]
