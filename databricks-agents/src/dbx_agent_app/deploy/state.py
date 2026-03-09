"""
Persistent deploy state stored in .agents-deploy.json.

Tracks deployed app names, URLs, service principal IDs, and timestamps
to enable idempotent re-deploys and clean teardown.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class AgentState(BaseModel):
    """Tracked state for a single deployed agent."""

    app_name: str
    url: str = ""
    sp_name: str = ""
    sp_client_id: str = ""
    deployed_at: str = ""


class DeployState(BaseModel):
    """Full deployment state persisted to disk."""

    project: str = ""
    profile: str = ""
    agents: dict[str, AgentState] = {}

    @classmethod
    def load(cls, path: str | Path) -> DeployState:
        """Load state from disk, or return empty state if file doesn't exist."""
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(**data)

    def save(self, path: str | Path) -> None:
        """Write state to disk."""
        path = Path(path)
        path.write_text(json.dumps(self.model_dump(), indent=2) + "\n")

    def set_agent(
        self,
        name: str,
        *,
        app_name: str,
        url: str = "",
        sp_name: str = "",
        sp_client_id: str = "",
    ) -> None:
        """Record or update state for a deployed agent."""
        self.agents[name] = AgentState(
            app_name=app_name,
            url=url,
            sp_name=sp_name,
            sp_client_id=sp_client_id,
            deployed_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_agent(self, name: str) -> AgentState | None:
        """Get state for a deployed agent, or None if not tracked."""
        return self.agents.get(name)

    def get_url(self, name: str) -> str:
        """Get the deployed URL for an agent."""
        agent = self.agents.get(name)
        return agent.url if agent else ""

    def remove_agent(self, name: str) -> None:
        """Remove agent from tracked state."""
        self.agents.pop(name, None)
