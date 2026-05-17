"""Tests for the eval bridge — app_predict_fn() and app_conversation_fn()."""

import json

import httpx
import pytest
import respx

from dbx_agent_app.bridge.eval import app_conversation_fn, app_predict_fn


APP_URL = "https://my-agent.cloud.databricks.com"
TOKEN = "dapi-test-token-123"


# -------------------------------------------------------------------
# Construction
# -------------------------------------------------------------------


def test_creates_predict_fn():
    fn = app_predict_fn(APP_URL, token=TOKEN)
    assert callable(fn)


def test_raises_without_token(monkeypatch):
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="No auth token"):
        app_predict_fn(APP_URL)


def test_reads_token_from_env(monkeypatch):
    monkeypatch.setenv("DATABRICKS_TOKEN", "env-token")
    fn = app_predict_fn(APP_URL)
    assert callable(fn)


# -------------------------------------------------------------------
# Calling predict_fn
# -------------------------------------------------------------------


AGENT_RESPONSE = {
    "output": [
        {
            "type": "message",
            "id": "abc-123",
            "content": [{"type": "output_text", "text": "Hello from agent!"}],
        }
    ]
}


@respx.mock
def test_predict_with_messages():
    route = respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(messages=[{"role": "user", "content": "Hi"}])

    assert route.called
    request_body = json.loads(route.calls[0].request.content)
    assert request_body == {"input": [{"role": "user", "content": "Hi"}]}

    assert result["response"] == "Hello from agent!"
    assert len(result["output"]) == 1


@respx.mock
def test_predict_with_question_kwarg():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(question="What is Databricks?")

    assert result["response"] == "Hello from agent!"


@respx.mock
def test_predict_with_input_kwarg():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(input="Tell me about agents")

    assert result["response"] == "Hello from agent!"


@respx.mock
def test_predict_with_query_kwarg():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(query="Search for experts")

    assert result["response"] == "Hello from agent!"


def test_predict_raises_without_input():
    fn = app_predict_fn(APP_URL, token=TOKEN)
    with pytest.raises(ValueError, match="requires 'messages'"):
        fn()


# -------------------------------------------------------------------
# Wire format translation
# -------------------------------------------------------------------


@respx.mock
def test_multi_content_blocks():
    """Multiple content blocks are joined with newlines."""
    multi_response = {
        "output": [
            {
                "type": "message",
                "id": "1",
                "content": [
                    {"type": "output_text", "text": "First part."},
                    {"type": "output_text", "text": "Second part."},
                ],
            }
        ]
    }
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=multi_response)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(messages=[{"role": "user", "content": "Hi"}])

    assert result["response"] == "First part.\nSecond part."


@respx.mock
def test_multi_output_items():
    """Multiple output items have all their text joined."""
    multi_item_response = {
        "output": [
            {"type": "message", "id": "1", "content": [{"text": "A"}]},
            {"type": "message", "id": "2", "content": [{"text": "B"}]},
        ]
    }
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=multi_item_response)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(messages=[{"role": "user", "content": "Hi"}])

    assert result["response"] == "A\nB"


@respx.mock
def test_empty_output():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json={"output": []})
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    result = fn(messages=[{"role": "user", "content": "Hi"}])

    assert result["response"] == ""
    assert result["output"] == []


# -------------------------------------------------------------------
# Auth headers
# -------------------------------------------------------------------


@respx.mock
def test_sends_auth_header():
    route = respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    fn(messages=[{"role": "user", "content": "Hi"}])

    auth_header = route.calls[0].request.headers["authorization"]
    assert auth_header == f"Bearer {TOKEN}"


# -------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------


@respx.mock
def test_raises_on_http_error():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    with pytest.raises(httpx.HTTPStatusError):
        fn(messages=[{"role": "user", "content": "Hi"}])


@respx.mock
def test_trailing_slash_stripped():
    route = respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(f"{APP_URL}/", token=TOKEN)
    fn(messages=[{"role": "user", "content": "Hi"}])

    assert route.called


# -------------------------------------------------------------------
# Multi-turn conversation
# -------------------------------------------------------------------


@respx.mock
def test_multi_turn_messages():
    """Verify multi-turn conversation messages are forwarded correctly."""
    route = respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_predict_fn(APP_URL, token=TOKEN)
    messages = [
        {"role": "user", "content": "What is MLflow?"},
        {"role": "assistant", "content": "MLflow is an open-source platform..."},
        {"role": "user", "content": "How does it handle agents?"},
    ]
    fn(messages=messages)

    request_body = json.loads(route.calls[0].request.content)
    assert request_body["input"] == messages


# ===================================================================
# app_conversation_fn — ConversationSimulator adapter
# ===================================================================


def test_conversation_fn_creates_callable():
    fn = app_conversation_fn(APP_URL, token=TOKEN)
    assert callable(fn)


def test_conversation_fn_raises_without_token(monkeypatch):
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    with pytest.raises(ValueError, match="No auth token"):
        app_conversation_fn(APP_URL)


@respx.mock
def test_conversation_fn_returns_string():
    """ConversationSimulator requires str return, not dict."""
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    result = fn(input=[{"role": "user", "content": "Hi"}])

    assert isinstance(result, str)
    assert result == "Hello from agent!"


@respx.mock
def test_conversation_fn_sends_full_history():
    """Verifies the full conversation history is forwarded as input."""
    route = respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    history = [
        {"role": "user", "content": "What is MLflow?"},
        {"role": "assistant", "content": "MLflow is..."},
        {"role": "user", "content": "Tell me more"},
    ]
    fn(input=history)

    request_body = json.loads(route.calls[0].request.content)
    assert request_body == {"input": history}


@respx.mock
def test_conversation_fn_accepts_kwargs():
    """ConversationSimulator passes mlflow_session_id and context as kwargs."""
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=AGENT_RESPONSE)
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    result = fn(
        input=[{"role": "user", "content": "Hi"}],
        mlflow_session_id="sess-123",
        context={"goal": "test agent"},
    )
    assert result == "Hello from agent!"


@respx.mock
def test_conversation_fn_multi_content():
    """Multiple text blocks are joined."""
    multi = {
        "output": [
            {
                "type": "message",
                "id": "1",
                "content": [
                    {"type": "output_text", "text": "Part A."},
                    {"type": "output_text", "text": "Part B."},
                ],
            }
        ]
    }
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json=multi)
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    assert fn(input=[{"role": "user", "content": "Hi"}]) == "Part A.\nPart B."


@respx.mock
def test_conversation_fn_empty_output():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(200, json={"output": []})
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    assert fn(input=[{"role": "user", "content": "Hi"}]) == ""


@respx.mock
def test_conversation_fn_http_error():
    respx.post(f"{APP_URL}/invocations").mock(
        return_value=httpx.Response(500, text="Server Error")
    )

    fn = app_conversation_fn(APP_URL, token=TOKEN)
    with pytest.raises(httpx.HTTPStatusError):
        fn(input=[{"role": "user", "content": "Hi"}])
