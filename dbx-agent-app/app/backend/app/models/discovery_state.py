from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base


class DiscoveryState(Base):
    """
    Persisted discovery state.

    Single-row table tracking the current state of the MCP discovery process.
    Replaces in-memory state so it works correctly with multiple workers.
    """

    __tablename__ = "discovery_state"

    id = Column(Integer, primary_key=True, default=1)
    is_running = Column(Boolean, default=False, nullable=False)
    last_run_timestamp = Column(String(64), nullable=True)
    last_run_status = Column(String(32), nullable=True)
    last_run_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DiscoveryState(is_running={self.is_running}, status='{self.last_run_status}')>"
