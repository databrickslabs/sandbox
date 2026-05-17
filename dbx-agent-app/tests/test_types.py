"""Tests for AgentRequest, AgentResponse, and StreamEvent wire protocol types."""

import json

from dbx_agent_app.core.types import (
    AgentRequest,
    AgentResponse,
    InputItem,
    OutputItem,
    OutputTextContent,
    StreamEvent,
    UserContext,
)


# ===================================================================
# AgentRequest
# ===================================================================


def test_request_from_wire():
    """AgentRequest parses the standard wire format."""
    data = {"input": [{"role": "user", "content": "hello"}]}
    req = AgentRequest(**data)

    assert len(req.input) == 1
    assert req.input[0].role == "user"
    assert req.input[0].content == "hello"


def test_request_messages_alias():
    """.messages is an alias for .input."""
    req = AgentRequest(input=[InputItem(role="user", content="hi")])
    assert req.messages == req.input


def test_request_last_user_message():
    """.last_user_message returns the last user message."""
    req = AgentRequest(
        input=[
            InputItem(role="user", content="first"),
            InputItem(role="assistant", content="reply"),
            InputItem(role="user", content="second"),
        ]
    )
    assert req.last_user_message == "second"


def test_request_last_user_message_empty():
    """.last_user_message returns empty string when no user messages."""
    req = AgentRequest(input=[InputItem(role="system", content="prompt")])
    assert req.last_user_message == ""


def test_request_empty_input():
    """AgentRequest with empty input is valid."""
    req = AgentRequest(input=[])
    assert req.messages == []
    assert req.last_user_message == ""


# ===================================================================
# AgentResponse
# ===================================================================


def test_response_text():
    """AgentResponse.text() creates a single-item text response."""
    resp = AgentResponse.text("Hello!")
    assert len(resp.output) == 1
    assert resp.output[0].type == "message"
    assert len(resp.output[0].content) == 1
    assert resp.output[0].content[0].text == "Hello!"


def test_response_text_custom_id():
    """AgentResponse.text() accepts a custom item_id."""
    resp = AgentResponse.text("hi", item_id="custom-id")
    assert resp.output[0].id == "custom-id"


def test_response_from_dict_with_response_key():
    """AgentResponse.from_dict() uses the 'response' key as text."""
    resp = AgentResponse.from_dict({"response": "OK", "extra": 42})
    assert resp.output[0].content[0].text == "OK"


def test_response_from_dict_serializes():
    """AgentResponse.from_dict() serializes the whole dict when no 'response' key."""
    data = {"foo": "bar", "count": 3}
    resp = AgentResponse.from_dict(data)
    text = resp.output[0].content[0].text
    parsed = json.loads(text)
    assert parsed == data


def test_response_to_wire():
    """to_wire() produces the expected wire format."""
    resp = AgentResponse.text("test", item_id="id-1")
    wire = resp.to_wire()

    assert "output" in wire
    assert wire["output"][0]["type"] == "message"
    assert wire["output"][0]["id"] == "id-1"
    assert wire["output"][0]["content"][0]["type"] == "output_text"
    assert wire["output"][0]["content"][0]["text"] == "test"


def test_response_wire_roundtrip():
    """Wire format can be serialized to JSON and back."""
    resp = AgentResponse.text("roundtrip")
    wire = resp.to_wire()
    json_str = json.dumps(wire)
    parsed = json.loads(json_str)

    assert parsed["output"][0]["content"][0]["text"] == "roundtrip"


# ===================================================================
# StreamEvent
# ===================================================================


def test_stream_text_delta():
    """StreamEvent.text_delta() creates a delta event."""
    evt = StreamEvent.text_delta("chunk", item_id="s1")
    assert evt.type == "response.output_text.delta"
    assert evt.delta == "chunk"
    assert evt.item_id == "s1"
    assert evt.item is None


def test_stream_done():
    """StreamEvent.done() creates a done event with full text."""
    evt = StreamEvent.done("full text", item_id="s1")
    assert evt.type == "response.output_item.done"
    assert evt.item is not None
    assert evt.item.content[0].text == "full text"
    assert evt.item.id == "s1"


def test_stream_to_sse():
    """to_sse() produces valid SSE format."""
    evt = StreamEvent.text_delta("hi", item_id="s1")
    sse = evt.to_sse()

    assert sse.startswith("data: ")
    assert sse.endswith("\n\n")

    payload = json.loads(sse[len("data: "):].strip())
    assert payload["type"] == "response.output_text.delta"
    assert payload["delta"] == "hi"


def test_stream_done_to_sse():
    """Done event serializes correctly to SSE."""
    evt = StreamEvent.done("final", item_id="d1")
    sse = evt.to_sse()
    payload = json.loads(sse[len("data: "):].strip())

    assert payload["type"] == "response.output_item.done"
    assert payload["item"]["content"][0]["text"] == "final"


def test_stream_auto_generates_item_id():
    """StreamEvent.text_delta() auto-generates item_id when not provided."""
    evt = StreamEvent.text_delta("chunk")
    assert evt.item_id is not None
    assert len(evt.item_id) > 0


# ===================================================================
# UserContext
# ===================================================================


def test_user_context_is_authenticated_with_token():
    """is_authenticated returns True when access_token is present."""
    ctx = UserContext(access_token="tok-123", email="user@example.com")
    assert ctx.is_authenticated is True


def test_user_context_is_not_authenticated_without_token():
    """is_authenticated returns False when no access_token."""
    ctx = UserContext(email="user@example.com")
    assert ctx.is_authenticated is False


def test_user_context_as_forwarded_headers():
    """as_forwarded_headers() builds correct X-Forwarded-* dict."""
    ctx = UserContext(
        access_token="tok-abc",
        email="user@example.com",
        user="user@example.com",
    )
    headers = ctx.as_forwarded_headers()
    assert headers["X-Forwarded-Access-Token"] == "tok-abc"
    assert headers["X-Forwarded-Email"] == "user@example.com"
    assert headers["X-Forwarded-User"] == "user@example.com"


def test_user_context_as_forwarded_headers_partial():
    """as_forwarded_headers() omits None fields."""
    ctx = UserContext(access_token="tok-abc")
    headers = ctx.as_forwarded_headers()
    assert "X-Forwarded-Access-Token" in headers
    assert "X-Forwarded-Email" not in headers
    assert "X-Forwarded-User" not in headers


def test_user_context_get_workspace_client_raises_without_token():
    """get_workspace_client() raises ValueError when no token."""
    ctx = UserContext(email="user@example.com")
    import pytest
    with pytest.raises(ValueError, match="No user access token"):
        ctx.get_workspace_client()


def test_user_context_repr_hides_token():
    """repr() does not expose the access_token value."""
    ctx = UserContext(access_token="secret-token-123", email="user@example.com")
    r = repr(ctx)
    assert "secret-token-123" not in r


def test_user_context_empty():
    """UserContext with no fields is valid but not authenticated."""
    ctx = UserContext()
    assert ctx.is_authenticated is False
    assert ctx.as_forwarded_headers() == {}


# ===================================================================
# AgentRequest — user_context
# ===================================================================


def test_request_user_context_default_none():
    """AgentRequest.user_context is None by default."""
    req = AgentRequest(input=[InputItem(role="user", content="hi")])
    assert req.user_context is None


def test_request_user_context_set_via_private_attr():
    """user_context can be set via _user_context and read via property."""
    req = AgentRequest(input=[InputItem(role="user", content="hi")])
    ctx = UserContext(access_token="tok", email="user@example.com")
    req._user_context = ctx

    assert req.user_context is ctx
    assert req.user_context.email == "user@example.com"


def test_request_model_dump_excludes_user_context():
    """model_dump() does not include _user_context (wire format unchanged)."""
    req = AgentRequest(input=[InputItem(role="user", content="hi")])
    req._user_context = UserContext(access_token="tok")

    dump = req.model_dump()
    assert "_user_context" not in dump
    assert "user_context" not in dump
    assert "input" in dump
