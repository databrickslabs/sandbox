"""Tests for A2AClient — agent-to-agent communication."""

import json
import pytest
import httpx
import respx

from dbx_agent_app.discovery.a2a_client import A2AClient, A2AClientError


AGENT_CARD = {
    "name": "test_agent",
    "description": "A test agent",
    "capabilities": ["search"],
    "version": "1.0.0",
}


# --- fetch_agent_card ---


@pytest.mark.asyncio
async def test_fetch_agent_card_success():
    """Fetches agent card from /.well-known/agent.json."""
    with respx.mock:
        respx.get("https://agent.example.com/.well-known/agent.json").mock(
            return_value=httpx.Response(200, json=AGENT_CARD)
        )

        async with A2AClient() as client:
            card = await client.fetch_agent_card("https://agent.example.com")

    assert card["name"] == "test_agent"
    assert card["capabilities"] == ["search"]


@pytest.mark.asyncio
async def test_fetch_agent_card_fallback_path():
    """Falls back to /card when /.well-known/agent.json fails."""
    with respx.mock:
        respx.get("https://agent.example.com/.well-known/agent.json").mock(
            return_value=httpx.Response(404)
        )
        respx.get("https://agent.example.com/card").mock(
            return_value=httpx.Response(200, json=AGENT_CARD)
        )

        async with A2AClient() as client:
            card = await client.fetch_agent_card("https://agent.example.com")

    assert card["name"] == "test_agent"


@pytest.mark.asyncio
async def test_fetch_agent_card_oauth_redirect():
    """Detects OAuth redirect and tries fallback path."""
    with respx.mock:
        respx.get("https://agent.example.com/.well-known/agent.json").mock(
            return_value=httpx.Response(302, headers={"Location": "https://login.example.com"})
        )
        respx.get("https://agent.example.com/card").mock(
            return_value=httpx.Response(302, headers={"Location": "https://login.example.com"})
        )

        async with A2AClient() as client:
            with pytest.raises(A2AClientError, match="Could not fetch agent card"):
                await client.fetch_agent_card("https://agent.example.com")


@pytest.mark.asyncio
async def test_fetch_agent_card_all_paths_fail():
    """Raises A2AClientError when all paths fail."""
    with respx.mock:
        respx.get("https://agent.example.com/.well-known/agent.json").mock(
            return_value=httpx.Response(404)
        )
        respx.get("https://agent.example.com/card").mock(
            return_value=httpx.Response(404)
        )

        async with A2AClient() as client:
            with pytest.raises(A2AClientError, match="Could not fetch agent card"):
                await client.fetch_agent_card("https://agent.example.com")


@pytest.mark.asyncio
async def test_fetch_agent_card_not_initialized():
    """Raises if client used outside context manager."""
    client = A2AClient()
    with pytest.raises(A2AClientError, match="not initialized"):
        await client.fetch_agent_card("https://agent.example.com")


# --- send_message ---


@pytest.mark.asyncio
async def test_send_message_success():
    """Sends a message and returns the result."""
    jsonrpc_response = {
        "jsonrpc": "2.0",
        "id": "abc",
        "result": {"status": "ok", "text": "Hello back"},
    }

    with respx.mock:
        route = respx.post("https://agent.example.com/api/a2a").mock(
            return_value=httpx.Response(200, json=jsonrpc_response)
        )

        async with A2AClient() as client:
            result = await client.send_message(
                "https://agent.example.com/api/a2a",
                "Hello agent",
            )

    assert result["status"] == "ok"
    # Verify the request payload structure
    sent = json.loads(route.calls[0].request.content)
    assert sent["method"] == "message/send"
    assert sent["params"]["message"]["parts"][0]["text"] == "Hello agent"


@pytest.mark.asyncio
async def test_send_message_with_context_id():
    """Context ID is included in the message payload."""
    with respx.mock:
        route = respx.post("https://agent.example.com/api/a2a").mock(
            return_value=httpx.Response(200, json={
                "jsonrpc": "2.0", "id": "x", "result": {},
            })
        )

        async with A2AClient() as client:
            await client.send_message(
                "https://agent.example.com/api/a2a",
                "Follow up",
                context_id="ctx-123",
            )

    sent = json.loads(route.calls[0].request.content)
    assert sent["params"]["message"]["contextId"] == "ctx-123"


@pytest.mark.asyncio
async def test_send_message_jsonrpc_error():
    """Raises A2AClientError when JSON-RPC returns an error."""
    with respx.mock:
        respx.post("https://agent.example.com/api/a2a").mock(
            return_value=httpx.Response(200, json={
                "jsonrpc": "2.0",
                "id": "x",
                "error": {"code": -32600, "message": "Invalid request"},
            })
        )

        async with A2AClient() as client:
            with pytest.raises(A2AClientError, match="Invalid request"):
                await client.send_message(
                    "https://agent.example.com/api/a2a", "test"
                )


@pytest.mark.asyncio
async def test_send_message_timeout():
    """Raises A2AClientError on timeout."""
    with respx.mock:
        respx.post("https://agent.example.com/api/a2a").mock(
            side_effect=httpx.ReadTimeout("timed out")
        )

        async with A2AClient(timeout=1.0) as client:
            with pytest.raises(A2AClientError, match="timed out"):
                await client.send_message(
                    "https://agent.example.com/api/a2a", "test"
                )


@pytest.mark.asyncio
async def test_send_message_http_error():
    """Raises A2AClientError on HTTP error status."""
    with respx.mock:
        respx.post("https://agent.example.com/api/a2a").mock(
            return_value=httpx.Response(500)
        )

        async with A2AClient() as client:
            with pytest.raises(A2AClientError, match="500"):
                await client.send_message(
                    "https://agent.example.com/api/a2a", "test"
                )


# --- send_streaming_message ---


@pytest.mark.asyncio
async def test_send_streaming_message_parses_sse():
    """Parses SSE data lines into JSON objects."""
    sse_body = (
        'data: {"type": "chunk", "text": "Hello"}\n\n'
        'data: {"type": "chunk", "text": " world"}\n\n'
        'data: {"type": "done"}\n\n'
    )

    with respx.mock:
        respx.post("https://agent.example.com/api/a2a/stream").mock(
            return_value=httpx.Response(
                200,
                content=sse_body.encode(),
                headers={"content-type": "text/event-stream"},
            )
        )

        events = []
        async with A2AClient() as client:
            async for event in client.send_streaming_message(
                "https://agent.example.com/api/a2a", "Stream test"
            ):
                events.append(event)

    assert len(events) == 3
    assert events[0]["text"] == "Hello"
    assert events[2]["type"] == "done"
