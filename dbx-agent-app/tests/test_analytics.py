"""Tests for the in-memory analytics tracker."""

from dbx_agent_app.dashboard.analytics import AnalyticsTracker


def test_empty_summary():
    tracker = AnalyticsTracker()
    summary = tracker.get_summary("unknown")
    assert summary["total"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["recent"] == []


def test_record_and_summary():
    tracker = AnalyticsTracker()
    tracker.record("agent-a", success=True, latency_ms=100, source="test")
    tracker.record("agent-a", success=True, latency_ms=200, source="chat")
    tracker.record("agent-a", success=False, latency_ms=50, source="test", error="timeout")

    summary = tracker.get_summary("agent-a")
    assert summary["total"] == 3
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 1
    assert summary["success_rate"] == round(2 / 3, 3)
    assert summary["avg_latency_ms"] == round((100 + 200 + 50) / 3)
    assert len(summary["recent"]) == 3


def test_ring_buffer_eviction():
    tracker = AnalyticsTracker(max_per_agent=5)
    for i in range(10):
        tracker.record("agent-b", success=True, latency_ms=i * 10, source="test")

    summary = tracker.get_summary("agent-b")
    assert summary["total"] == 5


def test_separate_agents():
    tracker = AnalyticsTracker()
    tracker.record("a", success=True, latency_ms=100, source="test")
    tracker.record("b", success=False, latency_ms=200, source="chat")

    assert tracker.get_summary("a")["success_count"] == 1
    assert tracker.get_summary("b")["failure_count"] == 1
    assert tracker.get_summary("a")["total"] == 1


def test_recent_order_is_newest_first():
    tracker = AnalyticsTracker()
    tracker.record("x", success=True, latency_ms=10, source="test")
    tracker.record("x", success=False, latency_ms=20, source="chat")

    recent = tracker.get_summary("x")["recent"]
    assert recent[0]["latency_ms"] == 20  # newest first
    assert recent[1]["latency_ms"] == 10


def test_error_field_recorded():
    tracker = AnalyticsTracker()
    tracker.record("x", success=False, latency_ms=0, source="test", error="connection refused")

    recent = tracker.get_summary("x")["recent"]
    assert recent[0]["error"] == "connection refused"
    assert recent[0]["success"] is False
