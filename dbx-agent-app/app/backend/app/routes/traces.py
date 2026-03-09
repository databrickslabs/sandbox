"""
SSE events and trace span endpoints for chat tracing.

Provides:
- GET /events?trace_id=X — SSE stream of trace events for a chat request
- GET /traces/{trace_id} — JSON span data for a trace
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Traces"])


async def _event_stream(trace_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE messages from stored trace events."""
    from app.routes.chat import trace_events

    events = trace_events.get(trace_id, [])
    for event in events:
        event_type = event.get("type", "message")
        data = json.dumps(event.get("data", {}))
        yield f"event: {event_type}\ndata: {data}\n\n"


@router.get("/events")
async def stream_events(trace_id: str = Query(..., description="Trace ID to stream events for")):
    """
    SSE endpoint that replays stored trace events for a given trace_id.

    The chat endpoint is synchronous, so all events are already stored
    by the time the frontend connects. Events are streamed and then the
    connection closes.
    """
    from app.routes.chat import trace_events

    if trace_id not in trace_events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No events found for trace_id {trace_id}",
        )

    return StreamingResponse(
        _event_stream(trace_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Return span data for a given trace.

    First checks in-memory store (fast path for current session).
    Falls back to MLflow for traces that survived a server restart.
    """
    from app.routes.chat import trace_spans

    # Fast path: in-memory data from current session
    if trace_id in trace_spans:
        return {
            "trace_id": trace_id,
            "spans": trace_spans[trace_id],
        }

    # Fallback: fetch from MLflow persistence
    try:
        from mlflow.client import MlflowClient
        client = MlflowClient()
        trace = client.get_trace(trace_id)
        if trace and trace.data and trace.data.spans:
            spans = []
            for s in trace.data.spans:
                spans.append({
                    "id": s.span_id,
                    "trace_id": trace_id,
                    "name": s.name,
                    "start_time": s.start_time_ns // 1_000_000 if s.start_time_ns else 0,
                    "end_time": s.end_time_ns // 1_000_000 if s.end_time_ns else 0,
                    "attributes": dict(s.attributes) if s.attributes else {},
                    "status": "ERROR" if s.status and str(s.status).upper() == "ERROR" else "OK",
                })
            return {
                "trace_id": trace_id,
                "spans": spans,
            }
    except Exception as e:
        logger.warning("MLflow trace fallback failed for %s: %s", trace_id, e)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No trace data found for trace_id {trace_id}",
    )
