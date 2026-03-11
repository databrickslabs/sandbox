"""In-memory analytics tracker for agent invocations."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class InvocationRecord:
    timestamp: float
    success: bool
    latency_ms: int
    source: str  # "test" | "chat" | "evaluate"
    error: str | None = None


class AnalyticsTracker:
    """In-memory ring buffer of recent agent invocations."""

    def __init__(self, max_per_agent: int = 100):
        self._max = max_per_agent
        self._records: dict[str, deque[InvocationRecord]] = {}

    def record(
        self,
        agent_name: str,
        *,
        success: bool,
        latency_ms: int,
        source: str,
        error: str | None = None,
    ) -> None:
        buf = self._records.setdefault(agent_name, deque(maxlen=self._max))
        buf.append(InvocationRecord(
            timestamp=time.time(),
            success=success,
            latency_ms=latency_ms,
            source=source,
            error=error,
        ))

    def get_summary(self, agent_name: str) -> dict[str, Any]:
        buf = self._records.get(agent_name)
        if not buf:
            return {
                "total": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0,
                "recent": [],
            }

        records = list(buf)
        total = len(records)
        success_count = sum(1 for r in records if r.success)
        failure_count = total - success_count
        avg_latency = sum(r.latency_ms for r in records) / total if total else 0

        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_count / total, 3) if total else 0.0,
            "avg_latency_ms": round(avg_latency),
            "recent": [asdict(r) for r in reversed(records[-20:])],
        }
