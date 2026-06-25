"""Tests for the optional MLflow tracing integration."""

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_trace_handler_no_mlflow():
    """When mlflow is not installed, trace_handler returns the function unchanged."""
    import dbx_agent_app.core.tracing as tracing_mod

    # Reset cached state
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": None}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        def my_func(x):
            return x

        result = tracing_mod.trace_handler(my_func, name="test")
        assert result is my_func


def test_trace_handler_with_mlflow():
    """When mlflow is installed, trace_handler wraps the function."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    wrapped_fn = MagicMock()
    mock_mlflow.trace.return_value = lambda f: wrapped_fn

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        def my_func(x):
            return x

        result = tracing_mod.trace_handler(
            my_func, name="test-agent", span_type="AGENT", attributes={"v": "1.0"}
        )
        assert result is wrapped_fn
        mock_mlflow.trace.assert_called_once_with(
            name="test-agent", span_type="AGENT", attributes={"v": "1.0"}
        )


def test_trace_tool():
    """trace_tool is a convenience for span_type=TOOL."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    wrapped_fn = MagicMock()
    mock_mlflow.trace.return_value = lambda f: wrapped_fn

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        def search(q: str):
            return []

        result = tracing_mod.trace_tool(search, name="search")
        assert result is wrapped_fn
        mock_mlflow.trace.assert_called_once_with(
            name="search", span_type="TOOL", attributes={}
        )


def test_trace_handler_mlflow_error_fallback():
    """If mlflow.trace raises, fall back to the original function."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    mock_mlflow.trace.side_effect = RuntimeError("broken")

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        def my_func(x):
            return x

        result = tracing_mod.trace_handler(my_func, name="test")
        assert result is my_func


def test_get_mlflow_caches():
    """_get_mlflow caches the result after first check."""
    import dbx_agent_app.core.tracing as tracing_mod

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": None}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        result1 = tracing_mod._get_mlflow()
        assert result1 is None
        assert tracing_mod._checked is True

        # Second call should use cached value
        result2 = tracing_mod._get_mlflow()
        assert result2 is None


# ===================================================================
# set_active_model
# ===================================================================


def test_set_active_model_with_mlflow():
    """When mlflow is available, calls mlflow.set_active_model."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.set_active_model("research")
        mock_mlflow.set_active_model.assert_called_once_with(name="research")


def test_set_active_model_no_mlflow():
    """When mlflow is not installed, set_active_model is a no-op."""
    import dbx_agent_app.core.tracing as tracing_mod

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": None}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.set_active_model("research")  # Should not raise


def test_set_active_model_error_fallback():
    """If set_active_model raises, it's caught silently."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    mock_mlflow.set_active_model.side_effect = RuntimeError("no experiment")
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.set_active_model("research")  # Should not raise


# ===================================================================
# update_trace
# ===================================================================


def test_update_trace_with_mlflow():
    """When mlflow is available, calls update_current_trace."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.update_trace(
            tags={"user_id": "u123"},
            metadata={"session": "s456"},
        )
        mock_mlflow.update_current_trace.assert_called_once_with(
            tags={"user_id": "u123"},
            metadata={"session": "s456"},
        )


def test_update_trace_no_mlflow():
    """No-op when mlflow is not installed."""
    import dbx_agent_app.core.tracing as tracing_mod

    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": None}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.update_trace(tags={"x": "y"})  # Should not raise


def test_update_trace_tags_only():
    """Can pass tags without metadata."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.update_trace(tags={"user": "alice"})
        mock_mlflow.update_current_trace.assert_called_once_with(tags={"user": "alice"})


def test_update_trace_noop_when_empty():
    """Passing no tags and no metadata skips the call."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.update_trace()
        mock_mlflow.update_current_trace.assert_not_called()


def test_update_trace_error_fallback():
    """If update_current_trace raises, it's caught silently."""
    import dbx_agent_app.core.tracing as tracing_mod

    mock_mlflow = MagicMock()
    mock_mlflow.update_current_trace.side_effect = RuntimeError("no active trace")
    tracing_mod._mlflow = None
    tracing_mod._checked = False

    with patch.dict(sys.modules, {"mlflow": mock_mlflow}):
        tracing_mod._mlflow = None
        tracing_mod._checked = False

        tracing_mod.update_trace(tags={"x": "y"})  # Should not raise
