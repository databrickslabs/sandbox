"""Tests for the System Builder service — CRUD, validation, deploy logic."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from databricks_agents.discovery import DiscoveredAgent
from databricks_agents.dashboard.scanner import DashboardScanner
from databricks_agents.dashboard.app import create_dashboard_app
from databricks_agents.dashboard.system_builder import (
    SystemBuilderService,
    SystemCreate,
    SystemUpdate,
    WiringEdge,
    DeployProgress,
)


# --- Fixtures ----------------------------------------------------------------

FAKE_AGENTS = [
    DiscoveredAgent(
        name="research_agent",
        endpoint_url="https://research.example.com",
        app_name="research-app",
        description="Does research",
        capabilities="search,analysis",
        protocol_version="a2a/1.0",
    ),
    DiscoveredAgent(
        name="data_agent",
        endpoint_url="https://data.example.com",
        app_name="data-app",
        description="Queries data",
        capabilities="sql",
        protocol_version="a2a/1.0",
    ),
    DiscoveredAgent(
        name="supervisor",
        endpoint_url="https://supervisor.example.com",
        app_name="supervisor-app",
        description="Orchestrates agents",
        capabilities="research_agent,data_agent",
        protocol_version="a2a/1.0",
    ),
]


@pytest.fixture
def scanner():
    """DashboardScanner pre-loaded with fake agents."""
    s = DashboardScanner.__new__(DashboardScanner)
    s._discovery = MagicMock()
    s._agents = list(FAKE_AGENTS)
    s._scan_lock = __import__("asyncio").Lock()
    s._scanned = True

    async def _mock_scan():
        return list(FAKE_AGENTS)
    s.scan = _mock_scan

    return s


@pytest.fixture
def service(scanner, tmp_path):
    """SystemBuilderService with temporary storage."""
    return SystemBuilderService(
        scanner=scanner,
        profile=None,
        data_dir=tmp_path,
    )


@pytest.fixture
def dashboard_client(scanner, tmp_path):
    """FastAPI TestClient with system builder enabled."""
    svc = SystemBuilderService(
        scanner=scanner,
        profile=None,
        data_dir=tmp_path,
    )
    app = create_dashboard_app(
        scanner, profile="test", system_builder=svc, auto_scan_interval=0
    )
    return TestClient(app)


# --- CRUD Tests --------------------------------------------------------------


def test_create_system(service):
    """Creating a system persists it and assigns an ID."""
    defn = service.create_system(SystemCreate(
        name="Test System",
        description="A test",
        agents=["research_agent", "data_agent"],
        edges=[WiringEdge(
            source_agent="research_agent",
            target_agent="data_agent",
            env_var="RESEARCH_URL",
        )],
    ))

    assert defn.id
    assert defn.name == "Test System"
    assert len(defn.agents) == 2
    assert len(defn.edges) == 1
    assert defn.edges[0].env_var == "RESEARCH_URL"


def test_list_systems(service):
    """List returns all created systems."""
    service.create_system(SystemCreate(name="System A", agents=[]))
    service.create_system(SystemCreate(name="System B", agents=[]))

    systems = service.list_systems()
    assert len(systems) == 2
    names = {s.name for s in systems}
    assert names == {"System A", "System B"}


def test_get_system(service):
    """Get by ID returns the correct system."""
    created = service.create_system(SystemCreate(name="Lookup Test", agents=[]))
    found = service.get_system(created.id)

    assert found is not None
    assert found.name == "Lookup Test"


def test_get_system_not_found(service):
    """Get with invalid ID returns None."""
    assert service.get_system("nonexistent-id") is None


def test_update_system(service):
    """Updating a system modifies only specified fields."""
    created = service.create_system(SystemCreate(
        name="Original",
        description="Before",
        agents=["research_agent"],
    ))

    updated = service.update_system(created.id, SystemUpdate(
        name="Updated",
        agents=["research_agent", "data_agent"],
    ))

    assert updated is not None
    assert updated.name == "Updated"
    assert updated.description == "Before"  # unchanged
    assert len(updated.agents) == 2


def test_update_system_not_found(service):
    """Updating a nonexistent system returns None."""
    result = service.update_system("bad-id", SystemUpdate(name="Nope"))
    assert result is None


def test_delete_system(service):
    """Deleting a system removes it from the store."""
    created = service.create_system(SystemCreate(name="To Delete", agents=[]))
    assert service.delete_system(created.id) is True
    assert service.get_system(created.id) is None
    assert service.delete_system(created.id) is False


def test_persistence(scanner, tmp_path):
    """Systems survive service restart (reload from JSON)."""
    svc1 = SystemBuilderService(scanner=scanner, data_dir=tmp_path)
    svc1.create_system(SystemCreate(name="Persistent", agents=["research_agent"]))

    # Create a new service instance that reads from same path
    svc2 = SystemBuilderService(scanner=scanner, data_dir=tmp_path)
    systems = svc2.list_systems()

    assert len(systems) == 1
    assert systems[0].name == "Persistent"


# --- Validation Tests ---------------------------------------------------------


def test_self_loop_rejected(service):
    """Edges where source == target are rejected."""
    with pytest.raises(ValueError, match="Self-loop"):
        service.create_system(SystemCreate(
            name="Self Loop",
            agents=["research_agent"],
            edges=[WiringEdge(
                source_agent="research_agent",
                target_agent="research_agent",
                env_var="SELF_URL",
            )],
        ))


def test_edge_source_not_in_agents(service):
    """Edges referencing agents not in the agents list are rejected."""
    with pytest.raises(ValueError, match="not in agents"):
        service.create_system(SystemCreate(
            name="Bad Edge",
            agents=["data_agent"],
            edges=[WiringEdge(
                source_agent="nonexistent",
                target_agent="data_agent",
                env_var="X_URL",
            )],
        ))


def test_edge_target_not_in_agents(service):
    """Edges referencing unknown target agents are rejected."""
    with pytest.raises(ValueError, match="not in agents"):
        service.create_system(SystemCreate(
            name="Bad Target",
            agents=["research_agent"],
            edges=[WiringEdge(
                source_agent="research_agent",
                target_agent="nonexistent",
                env_var="X_URL",
            )],
        ))


# --- Deploy Tests (with mocked Databricks APIs) ------------------------------


@pytest.mark.asyncio
async def test_deploy_system_not_found(service):
    """Deploy for nonexistent system returns failed result."""
    result = await service.deploy_system("nonexistent")
    assert result.status == "failed"
    assert len(result.steps) == 1
    assert result.steps[0].status == "failed"


@pytest.mark.asyncio
async def test_deploy_resolves_agents(service):
    """Deploy resolves agent metadata from scanner."""
    defn = service.create_system(SystemCreate(
        name="Deploy Test",
        agents=["research_agent", "data_agent"],
        edges=[WiringEdge(
            source_agent="research_agent",
            target_agent="data_agent",
            env_var="RESEARCH_URL",
        )],
    ))

    # Mock workspace client to avoid real API calls
    with patch.object(service, '_get_ws_client', return_value=None):
        result = await service.deploy_system(defn.id)

    # Without ws_client, env_update and permissions are skipped
    assert result.system_id == defn.id
    # Should have skipped steps due to no workspace client
    skipped = [s for s in result.steps if s.status == "skipped"]
    assert len(skipped) > 0


@pytest.mark.asyncio
async def test_deploy_unresolved_agent(service):
    """Deploy reports failure for agents not found in scanner."""
    defn = service.create_system(SystemCreate(
        name="Missing Agent",
        agents=["unknown_agent"],
        edges=[],
    ))

    # Scanner won't find "unknown_agent"
    with patch.object(service, '_get_ws_client', return_value=None):
        result = await service.deploy_system(defn.id)

    failed = [s for s in result.steps if s.status == "failed" and s.action == "resolve"]
    assert len(failed) == 1
    assert "not found" in failed[0].detail


# --- API Route Tests ----------------------------------------------------------


def test_api_list_systems_empty(dashboard_client):
    """GET /api/systems returns empty list initially."""
    resp = dashboard_client.get("/api/systems")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_create_and_get_system(dashboard_client):
    """POST /api/systems creates, GET /api/systems/{id} retrieves."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "API Test",
        "agents": ["research_agent", "data_agent"],
        "edges": [{
            "source_agent": "research_agent",
            "target_agent": "data_agent",
            "env_var": "RESEARCH_URL",
        }],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "API Test"
    system_id = data["id"]

    # GET by ID
    resp2 = dashboard_client.get(f"/api/systems/{system_id}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "API Test"


def test_api_update_system(dashboard_client):
    """PUT /api/systems/{id} updates the system."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "Before Update",
        "agents": [],
    })
    system_id = resp.json()["id"]

    resp2 = dashboard_client.put(f"/api/systems/{system_id}", json={
        "name": "After Update",
    })
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "After Update"


def test_api_delete_system(dashboard_client):
    """DELETE /api/systems/{id} removes the system."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "To Delete",
        "agents": [],
    })
    system_id = resp.json()["id"]

    resp2 = dashboard_client.delete(f"/api/systems/{system_id}")
    assert resp2.status_code == 200

    resp3 = dashboard_client.get(f"/api/systems/{system_id}")
    assert resp3.status_code == 404


def test_api_create_system_validation_error(dashboard_client):
    """POST /api/systems returns 400 for invalid edges."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "Bad System",
        "agents": ["research_agent"],
        "edges": [{
            "source_agent": "research_agent",
            "target_agent": "research_agent",
            "env_var": "SELF_URL",
        }],
    })
    assert resp.status_code == 400
    assert "Self-loop" in resp.json()["error"]


def test_api_get_system_not_found(dashboard_client):
    """GET /api/systems/{id} returns 404 for unknown ID."""
    resp = dashboard_client.get("/api/systems/nonexistent")
    assert resp.status_code == 404


def test_api_deploy_system(dashboard_client):
    """POST /api/systems/{id}/deploy returns deploy result."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "Deploy Test",
        "agents": ["research_agent"],
        "edges": [],
    })
    system_id = resp.json()["id"]

    resp2 = dashboard_client.post(f"/api/systems/{system_id}/deploy")
    assert resp2.status_code == 200
    data = resp2.json()
    assert "system_id" in data
    assert "steps" in data
    assert "status" in data


# --- Async Deploy Tests -------------------------------------------------------


@pytest.mark.asyncio
async def test_start_deploy_returns_progress(service):
    """start_deploy returns DeployProgress with deploy_id and status='pending'."""
    defn = service.create_system(SystemCreate(
        name="Async Deploy Test",
        agents=["research_agent", "data_agent"],
        edges=[WiringEdge(
            source_agent="research_agent",
            target_agent="data_agent",
            env_var="RESEARCH_URL",
        )],
    ))

    with patch.object(service, '_get_ws_client', return_value=None):
        progress = service.start_deploy(defn.id)

    # Check immediately — before yielding to event loop
    assert isinstance(progress, DeployProgress)
    assert progress.deploy_id  # non-empty
    assert progress.system_id == defn.id
    assert progress.status == "pending"
    assert progress.total_steps > 0

    # Let background task finish to avoid warnings
    await asyncio.sleep(0.1)


def test_start_deploy_nonexistent_system(service):
    """start_deploy on a bad system_id returns status='failed'."""
    progress = service.start_deploy("nonexistent-system-id")

    assert isinstance(progress, DeployProgress)
    assert progress.status == "failed"
    assert len(progress.steps) == 1
    assert progress.steps[0].status == "failed"
    assert "not found" in progress.steps[0].detail


def test_get_deploy_status_none(service):
    """get_deploy_status returns None when no deploy is active."""
    defn = service.create_system(SystemCreate(
        name="No Deploy",
        agents=["research_agent"],
    ))

    result = service.get_deploy_status(defn.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_deploy_status_after_start(service):
    """After start_deploy, get_deploy_status returns the same deploy_id."""
    defn = service.create_system(SystemCreate(
        name="Status Check",
        agents=["research_agent"],
        edges=[],
    ))

    with patch.object(service, '_get_ws_client', return_value=None):
        progress = service.start_deploy(defn.id)
        # Allow the background task to run
        await asyncio.sleep(0.1)

    status = service.get_deploy_status(defn.id)
    assert status is not None
    assert status.deploy_id == progress.deploy_id
    assert status.system_id == defn.id


def test_api_deploy_async(dashboard_client):
    """POST /api/systems/{id}/deploy with {"async": true} returns deploy_id."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "Async API Test",
        "agents": ["research_agent"],
        "edges": [],
    })
    system_id = resp.json()["id"]

    resp2 = dashboard_client.post(
        f"/api/systems/{system_id}/deploy",
        json={"async": True},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert "deploy_id" in data
    assert data["system_id"] == system_id
    assert data["status"] in ("pending", "deploying", "success", "partial", "failed")


def test_api_deploy_status_not_found(dashboard_client):
    """GET /api/systems/{id}/deploy/status returns 404 when no deploy active."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "No Deploy Status",
        "agents": [],
    })
    system_id = resp.json()["id"]

    resp2 = dashboard_client.get(f"/api/systems/{system_id}/deploy/status")
    assert resp2.status_code == 404
    assert "No active deploy" in resp2.json()["error"]


def test_api_deploy_sync_still_works(dashboard_client):
    """POST /api/systems/{id}/deploy without body still returns full DeployResult."""
    resp = dashboard_client.post("/api/systems", json={
        "name": "Sync Compat Test",
        "agents": ["research_agent"],
        "edges": [],
    })
    system_id = resp.json()["id"]

    # No body — should fall back to sync deploy
    resp2 = dashboard_client.post(f"/api/systems/{system_id}/deploy")
    assert resp2.status_code == 200
    data = resp2.json()
    # Sync deploy returns DeployResult shape (system_id, steps, status)
    assert data["system_id"] == system_id
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert data["status"] in ("success", "partial", "failed")
