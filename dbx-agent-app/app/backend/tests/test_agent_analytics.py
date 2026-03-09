"""
Tests for agent analytics CRUD and the GET /agents/{id}/analytics endpoint.
"""

import pytest
from app.models.agent import Agent
from app.models.agent_analytics import AgentAnalytics
from app.db_adapter import DatabaseAdapter


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_agent(db):
    """Create a sample agent for analytics tests."""
    agent = Agent(
        name="analytics-test-agent",
        description="Agent for analytics tests",
        capabilities="search,summarize",
        status="active",
        endpoint_url="https://example.com/agent",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def sample_analytics(db, sample_agent):
    """Create sample analytics entries."""
    entries = [
        AgentAnalytics(agent_id=sample_agent.id, task_description="task 1", success=1, latency_ms=100, quality_score=4),
        AgentAnalytics(agent_id=sample_agent.id, task_description="task 2", success=1, latency_ms=200, quality_score=5),
        AgentAnalytics(agent_id=sample_agent.id, task_description="task 3", success=0, latency_ms=50, quality_score=2, error_message="timeout"),
    ]
    for e in entries:
        db.add(e)
    db.commit()
    return entries


# ── DatabaseAdapter CRUD tests ────────────────────────────────────────


class TestAnalyticsCrud:
    """Test analytics CRUD via DatabaseAdapter."""

    def test_create_agent_analytic(self, db, sample_agent):
        result = DatabaseAdapter.create_agent_analytic(
            agent_id=sample_agent.id,
            task_description="test task",
            success=1,
            latency_ms=150,
            quality_score=4,
        )
        assert result["agent_id"] == sample_agent.id
        assert result["task_description"] == "test task"
        assert result["success"] == 1
        assert result["latency_ms"] == 150
        assert result["quality_score"] == 4
        assert result["error_message"] is None
        assert "id" in result
        assert "created_at" in result

    def test_create_agent_analytic_failure(self, db, sample_agent):
        result = DatabaseAdapter.create_agent_analytic(
            agent_id=sample_agent.id,
            task_description="failing task",
            success=0,
            latency_ms=30,
            quality_score=1,
            error_message="connection refused",
        )
        assert result["success"] == 0
        assert result["error_message"] == "connection refused"

    def test_create_agent_analytic_minimal(self, db, sample_agent):
        """Create with only required field (agent_id)."""
        result = DatabaseAdapter.create_agent_analytic(agent_id=sample_agent.id)
        assert result["agent_id"] == sample_agent.id
        assert result["success"] == 1  # default
        assert result["task_description"] is None

    def test_list_agent_analytics(self, db, sample_agent, sample_analytics):
        results = DatabaseAdapter.list_agent_analytics(sample_agent.id)
        assert len(results) == 3

    def test_list_agent_analytics_limit(self, db, sample_agent, sample_analytics):
        results = DatabaseAdapter.list_agent_analytics(sample_agent.id, limit=2)
        assert len(results) == 2

    def test_list_agent_analytics_empty(self, db, sample_agent):
        results = DatabaseAdapter.list_agent_analytics(sample_agent.id)
        assert results == []

    def test_get_agent_summary_stats(self, db, sample_agent, sample_analytics):
        stats = DatabaseAdapter.get_agent_summary_stats(sample_agent.id)
        assert stats["agent_id"] == sample_agent.id
        assert stats["total_invocations"] == 3
        assert stats["success_count"] == 2
        assert stats["failure_count"] == 1
        assert stats["success_rate"] == pytest.approx(2 / 3, abs=0.001)
        assert stats["avg_latency_ms"] is not None
        # avg of 100, 200, 50 = 116.67
        assert stats["avg_latency_ms"] == pytest.approx(117, abs=1)
        # avg of 4, 5, 2 = 3.67
        assert stats["avg_quality_score"] == pytest.approx(3.67, abs=0.01)

    def test_get_agent_summary_stats_empty(self, db, sample_agent):
        stats = DatabaseAdapter.get_agent_summary_stats(sample_agent.id)
        assert stats["total_invocations"] == 0
        assert stats["success_rate"] is None
        assert stats["avg_latency_ms"] is None
        assert stats["avg_quality_score"] is None


# ── API endpoint tests ────────────────────────────────────────────────


class TestAnalyticsEndpoint:
    """Test GET /agents/{id}/analytics endpoint."""

    def test_get_analytics(self, client, db, sample_agent, sample_analytics):
        response = client.get(f"/api/agents/{sample_agent.id}/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == sample_agent.id
        assert data["agent_name"] == "analytics-test-agent"
        assert "summary" in data
        assert "recent" in data
        assert data["summary"]["total_invocations"] == 3
        assert len(data["recent"]) == 3

    def test_get_analytics_with_limit(self, client, db, sample_agent, sample_analytics):
        response = client.get(f"/api/agents/{sample_agent.id}/analytics?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recent"]) == 1

    def test_get_analytics_not_found(self, client, db):
        response = client.get("/api/agents/9999/analytics")
        assert response.status_code == 404

    def test_get_analytics_empty(self, client, db, sample_agent):
        response = client.get(f"/api/agents/{sample_agent.id}/analytics")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_invocations"] == 0
        assert data["recent"] == []
