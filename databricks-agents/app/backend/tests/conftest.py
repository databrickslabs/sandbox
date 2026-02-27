"""
Pytest fixtures for testing the Multi-Agent Registry API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import App, MCPServer, Tool, Collection, CollectionItem
import app.database as _database_module


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign key constraints in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """
    Create a fresh database for each test.
    Patches SessionLocal so the WarehouseDB adapter also uses the test engine.
    """
    Base.metadata.create_all(bind=engine)
    original_session_local = _database_module.SessionLocal
    _database_module.SessionLocal = TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        _database_module.SessionLocal = original_session_local
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """
    Create a test client with dependency override.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_app(db):
    """
    Create a sample app for testing.
    """
    app = App(
        name="test-app",
        owner="test@example.com",
        url="https://example.com/app",
        tags="test,sample",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@pytest.fixture
def sample_mcp_server(db, sample_app):
    """
    Create a sample MCP server for testing.
    """
    from app.models.mcp_server import MCPServerKind

    server = MCPServer(
        app_id=sample_app.id,
        server_url="https://example.com/mcp",
        kind=MCPServerKind.CUSTOM,
        scopes="read,write",
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@pytest.fixture
def sample_tool(db, sample_mcp_server):
    """
    Create a sample tool for testing.
    """
    tool = Tool(
        mcp_server_id=sample_mcp_server.id,
        name="test_tool",
        description="A test tool",
        parameters='{"type": "object"}',
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


@pytest.fixture
def sample_collection(db):
    """
    Create a sample collection for testing.
    """
    collection = Collection(
        name="Test Collection",
        description="A test collection",
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection
