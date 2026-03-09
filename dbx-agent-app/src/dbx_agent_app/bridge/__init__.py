"""
Bridge module for interoperability with the official ``databricks-agents`` package.

Provides ``app_predict_fn()`` which wraps a Databricks App's /invocations
endpoint as a ``predict_fn`` compatible with ``mlflow.genai.evaluate()``.
"""

from dbx_agent_app.bridge.eval import app_predict_fn

__all__ = ["app_predict_fn"]
