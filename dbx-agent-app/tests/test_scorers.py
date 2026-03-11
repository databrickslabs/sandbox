"""Tests for the built-in MLflow 3 scorers.

Since mlflow may not be installed in the test environment, these tests
mock the mlflow.genai.scorers module and verify the scorer logic directly.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_mlflow():
    """Create mock mlflow modules so scorers can import."""
    mock_mlflow = MagicMock()

    # Make @scorer a passthrough decorator
    def passthrough_scorer(func):
        return func

    mock_mlflow.genai.scorers.scorer = passthrough_scorer

    # Mock Feedback as a simple dataclass-like
    class MockFeedback:
        def __init__(self, value, rationale=None, **kwargs):
            self.value = value
            self.rationale = rationale

    mock_mlflow.entities.Feedback = MockFeedback

    return mock_mlflow, MockFeedback


@pytest.fixture(autouse=True)
def mock_mlflow_modules():
    """Inject mock mlflow into sys.modules for all tests in this file."""
    mock_mlflow, _ = _make_mock_mlflow()

    modules = {
        "mlflow": mock_mlflow,
        "mlflow.genai": mock_mlflow.genai,
        "mlflow.genai.scorers": mock_mlflow.genai.scorers,
        "mlflow.entities": mock_mlflow.entities,
    }

    # Remove cached scorers module if loaded
    sys.modules.pop("dbx_agent_app.bridge.scorers", None)

    with patch.dict(sys.modules, modules):
        yield mock_mlflow


def _import_scorers():
    """Import scorers module fresh (after mocking)."""
    sys.modules.pop("dbx_agent_app.bridge.scorers", None)
    from dbx_agent_app.bridge import scorers
    return scorers


class TestResponseNotEmpty:
    def test_non_empty(self, mock_mlflow_modules):
        scorers = _import_scorers()
        assert scorers.response_not_empty(outputs={"response": "Hello world"}) is True

    def test_empty_string(self, mock_mlflow_modules):
        scorers = _import_scorers()
        assert scorers.response_not_empty(outputs={"response": ""}) is False

    def test_whitespace_only(self, mock_mlflow_modules):
        scorers = _import_scorers()
        assert scorers.response_not_empty(outputs={"response": "   "}) is False

    def test_missing_response_key(self, mock_mlflow_modules):
        scorers = _import_scorers()
        assert scorers.response_not_empty(outputs={}) is False


class TestLatencyUnder:
    def test_under_threshold(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.latency_under(
            outputs={"latency_ms": 100},
            expectations={"max_latency_ms": 5000},
        )
        assert result.value is True
        assert "100ms" in result.rationale

    def test_over_threshold(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.latency_under(
            outputs={"latency_ms": 10000},
            expectations={"max_latency_ms": 5000},
        )
        assert result.value is False

    def test_default_threshold(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.latency_under(
            outputs={"latency_ms": 100},
            expectations={},
        )
        assert result.value is True  # default 5000ms


class TestToolWasCalled:
    def test_tool_found(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.tool_was_called(
            outputs={"tools_used": ["search", "summarize"]},
            expectations={"expected_tool": "search"},
        )
        assert result.value is True

    def test_tool_not_found(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.tool_was_called(
            outputs={"tools_used": ["summarize"]},
            expectations={"expected_tool": "search"},
        )
        assert result.value is False

    def test_no_expected_tool(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.tool_was_called(
            outputs={"tools_used": []},
            expectations={},
        )
        assert result.value is True  # no expectation = pass


class TestResponseContains:
    def test_all_present(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.response_contains(
            outputs={"response": "Guidepoint is a research firm"},
            expectations={"must_contain": ["Guidepoint", "research"]},
        )
        assert result.value is True

    def test_some_missing(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.response_contains(
            outputs={"response": "Guidepoint is a firm"},
            expectations={"must_contain": ["Guidepoint", "research"]},
        )
        assert result.value is False
        assert "research" in result.rationale

    def test_case_insensitive(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.response_contains(
            outputs={"response": "GUIDEPOINT Research"},
            expectations={"must_contain": ["guidepoint", "research"]},
        )
        assert result.value is True

    def test_string_instead_of_list(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.response_contains(
            outputs={"response": "Hello world"},
            expectations={"must_contain": "world"},
        )
        assert result.value is True

    def test_empty_must_contain(self, mock_mlflow_modules):
        scorers = _import_scorers()
        result = scorers.response_contains(
            outputs={"response": "anything"},
            expectations={"must_contain": []},
        )
        assert result.value is True


class TestMakeLlmRelevanceScorer:
    def test_creates_callable(self, mock_mlflow_modules):
        # Mock the judges module
        mock_judges = MagicMock()
        mock_result = MagicMock()
        mock_result.value = True
        mock_judges.is_correct.return_value = mock_result

        with patch.dict(sys.modules, {"mlflow.genai.judges": mock_judges}):
            scorers = _import_scorers()
            scorer_fn = scorers.make_llm_relevance_scorer("databricks-claude-sonnet-4")
            assert callable(scorer_fn)

    def test_calls_is_correct(self, mock_mlflow_modules):
        mock_judges = MagicMock()
        mock_result = MagicMock()
        mock_result.value = True
        mock_judges.is_correct.return_value = mock_result

        with patch.dict(sys.modules, {"mlflow.genai.judges": mock_judges}):
            scorers = _import_scorers()
            scorer_fn = scorers.make_llm_relevance_scorer()

            result = scorer_fn(
                inputs={"messages": [{"role": "user", "content": "What is MLflow?"}]},
                outputs={"response": "MLflow is a platform for ML lifecycle"},
                expectations={"expected_facts": ["ML lifecycle"]},
            )

            mock_judges.is_correct.assert_called_once_with(
                request="What is MLflow?",
                response="MLflow is a platform for ML lifecycle",
                expected_facts=["ML lifecycle"],
            )
            assert result is mock_result

    def test_extracts_last_user_message(self, mock_mlflow_modules):
        mock_judges = MagicMock()
        mock_judges.is_correct.return_value = MagicMock(value=True)

        with patch.dict(sys.modules, {"mlflow.genai.judges": mock_judges}):
            scorers = _import_scorers()
            scorer_fn = scorers.make_llm_relevance_scorer()

            scorer_fn(
                inputs={"messages": [
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "First answer"},
                    {"role": "user", "content": "Follow up"},
                ]},
                outputs={"response": "Some response"},
                expectations={},
            )

            # Should use the last user message
            call_kwargs = mock_judges.is_correct.call_args[1]
            assert call_kwargs["request"] == "Follow up"

    def test_string_expected_facts_converted_to_list(self, mock_mlflow_modules):
        mock_judges = MagicMock()
        mock_judges.is_correct.return_value = MagicMock(value=True)

        with patch.dict(sys.modules, {"mlflow.genai.judges": mock_judges}):
            scorers = _import_scorers()
            scorer_fn = scorers.make_llm_relevance_scorer()

            scorer_fn(
                inputs={"messages": [{"role": "user", "content": "Q"}]},
                outputs={"response": "A"},
                expectations={"expected_facts": "single fact"},
            )

            call_kwargs = mock_judges.is_correct.call_args[1]
            assert call_kwargs["expected_facts"] == ["single fact"]
