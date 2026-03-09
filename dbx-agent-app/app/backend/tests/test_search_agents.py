"""
Tests for agent search functionality — keyword search and embedding pipeline.
"""

import json
import pytest
from app.models.agent import Agent
from app.db_adapter import DatabaseAdapter
from app.services.search import SearchService
from app.services.embedding import EmbeddingService


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_agents(db):
    """Create sample agents for search tests."""
    agents = [
        Agent(
            name="transcript-search-agent",
            description="Searches expert transcripts using RAG",
            capabilities="search,rag,transcripts",
            status="active",
            endpoint_url="https://example.com/search-agent",
            skills='[{"name": "search_transcripts", "description": "RAG search"}]',
        ),
        Agent(
            name="profile-agent",
            description="Retrieves and summarizes expert profiles",
            capabilities="profiles,summarization",
            status="active",
            endpoint_url="https://example.com/profile-agent",
        ),
        Agent(
            name="inactive-agent",
            description="An inactive agent that should not match",
            capabilities="search",
            status="inactive",
            endpoint_url="https://example.com/inactive",
        ),
    ]
    for a in agents:
        db.add(a)
    db.commit()
    for a in agents:
        db.refresh(a)
    return agents


# ── Agent keyword search tests ────────────────────────────────────────


class TestAgentKeywordSearch:
    """Test that agents appear in keyword search results."""

    def test_search_finds_agent_by_name(self, db, sample_agents, client):
        """Search for agent by name via the search endpoint."""
        response = client.post(
            "/api/search",
            json={"query": "transcript-search", "types": ["agent"], "mode": "keyword"},
        )
        assert response.status_code == 200
        data = response.json()
        agent_results = [r for r in data["results"] if r["asset_type"] == "agent"]
        assert len(agent_results) >= 1
        assert any("transcript" in r["name"].lower() for r in agent_results)

    def test_search_finds_agent_by_description(self, db, sample_agents, client):
        """Search finds agent by description keywords."""
        response = client.post(
            "/api/search",
            json={"query": "expert profiles", "types": ["agent"], "mode": "keyword"},
        )
        assert response.status_code == 200
        data = response.json()
        agent_results = [r for r in data["results"] if r["asset_type"] == "agent"]
        assert len(agent_results) >= 1

    def test_search_finds_agent_by_capabilities(self, db, sample_agents, client):
        """Search finds agent by capabilities text."""
        response = client.post(
            "/api/search",
            json={"query": "rag", "types": ["agent"], "mode": "keyword"},
        )
        assert response.status_code == 200
        data = response.json()
        agent_results = [r for r in data["results"] if r["asset_type"] == "agent"]
        assert len(agent_results) >= 1

    def test_search_no_match(self, db, sample_agents, client):
        """Search for non-existent capability returns no agents."""
        response = client.post(
            "/api/search",
            json={"query": "zzz-nonexistent-xyz", "types": ["agent"], "mode": "keyword"},
        )
        assert response.status_code == 200
        data = response.json()
        agent_results = [r for r in data["results"] if r["asset_type"] == "agent"]
        assert len(agent_results) == 0


# ── Agent CRUD endpoint tests ────────────────────────────────────────


class TestAgentCrud:
    """Test basic agent CRUD to verify fixture setup works."""

    def test_list_agents(self, client, db, sample_agents):
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3

    def test_get_agent(self, client, db, sample_agents):
        agent = sample_agents[0]
        response = client.get(f"/api/agents/{agent.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "transcript-search-agent"

    def test_create_agent(self, client, db):
        response = client.post(
            "/api/agents",
            json={
                "name": "new-test-agent",
                "description": "A brand new agent",
                "capabilities": "testing",
                "status": "draft",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new-test-agent"
        assert "id" in data


# ── Embedding pipeline tests ─────────────────────────────────────────


class TestAgentEmbeddingText:
    """Test that _build_text produces searchable text for agents."""

    def _build(self, asset_type, asset):
        svc = EmbeddingService.__new__(EmbeddingService)
        return svc._build_text(asset_type, asset)

    def test_build_text_with_capabilities(self):
        asset = {
            "name": "my-agent",
            "description": "Does cool things",
            "capabilities": "search,summarize",
        }
        text = self._build("agent", asset)
        assert "my-agent" in text
        assert "Does cool things" in text
        assert "capabilities: search,summarize" in text

    def test_build_text_with_skills_json(self):
        asset = {
            "name": "skilled-agent",
            "description": "Multi-skilled",
            "skills": '[{"name": "search_docs"}, {"name": "summarize_text"}]',
        }
        text = self._build("agent", asset)
        assert "search_docs" in text
        assert "summarize_text" in text

    def test_build_text_with_invalid_skills_json(self):
        """Invalid skills JSON should not crash, just skip."""
        asset = {
            "name": "broken-skills-agent",
            "description": "Has bad skills JSON",
            "skills": "not valid json",
        }
        text = self._build("agent", asset)
        assert "broken-skills-agent" in text

    def test_build_text_minimal_agent(self):
        asset = {"name": "minimal-agent"}
        text = self._build("agent", asset)
        assert "minimal-agent" in text
