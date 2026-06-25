"""Optional MLflow 3 tracing integration.

Provides thin wrappers around ``@mlflow.trace`` that gracefully degrade
when MLflow is not installed.  All functions in this module are safe to
call regardless of whether the ``mlflow`` package is available.

``mlflow.trace`` natively supports sync, async, generator, and async
generator functions — one ``trace_handler`` call covers all paths.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_mlflow: Any = None
_checked = False


def _get_mlflow():
    """Lazily import mlflow. Returns the module or None."""
    global _mlflow, _checked
    if not _checked:
        try:
            import mlflow  # noqa: F811

            _mlflow = mlflow
        except ImportError:
            _mlflow = None
        _checked = True
    return _mlflow


def trace_handler(
    func: Callable,
    *,
    name: str,
    span_type: str = "AGENT",
    attributes: Optional[dict[str, Any]] = None,
) -> Callable:
    """Wrap *func* with ``@mlflow.trace`` if MLflow is available, else return as-is.

    Args:
        func: The function to trace (sync, async, generator, or async generator).
        name: Span name shown in the MLflow UI.
        span_type: Span type (``AGENT``, ``TOOL``, ``LLM``, etc.).
        attributes: Extra key-value pairs attached to the span.

    Returns:
        A traced version of *func*, or *func* unchanged if MLflow is absent.
    """
    mlflow = _get_mlflow()
    if mlflow is None:
        return func

    try:
        return mlflow.trace(
            name=name,
            span_type=span_type,
            attributes=attributes or {},
        )(func)
    except Exception:
        logger.debug("Failed to apply mlflow.trace to %s — tracing disabled", name)
        return func


def trace_tool(func: Callable, *, name: str) -> Callable:
    """Convenience wrapper: trace a tool function with span_type=TOOL."""
    return trace_handler(func, name=name, span_type="TOOL")


def set_active_model(name: str) -> None:
    """Link all subsequent traces to a registered LoggedModel.

    Call once at agent startup.  No-op if MLflow is not installed.
    """
    mlflow = _get_mlflow()
    if mlflow is None:
        return
    try:
        mlflow.set_active_model(name=name)
        logger.debug("Active model set to %s", name)
    except Exception:
        logger.debug("Failed to set active model %s — model linking disabled", name)


def update_trace(
    tags: Optional[dict[str, str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Enrich the current active trace with request-specific context.

    Safe to call from handler code without importing mlflow directly.
    No-op if MLflow is not installed or no trace is active.

    Args:
        tags: Key-value pairs surfaced in the MLflow UI (e.g. user_id, session).
        metadata: Arbitrary JSON-serializable data attached to the trace.
    """
    mlflow = _get_mlflow()
    if mlflow is None:
        return
    try:
        kwargs: dict[str, Any] = {}
        if tags:
            kwargs["tags"] = tags
        if metadata:
            kwargs["metadata"] = metadata
        if kwargs:
            mlflow.update_current_trace(**kwargs)
    except Exception:
        logger.debug("Failed to update current trace")
