import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings
from typing import Generator

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with NullPool for OBO (On-Behalf-Of) support
# NullPool ensures each request gets a fresh connection with the user's identity
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,  # Required for OBO - no connection pooling
    echo=settings.debug,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# Base class for all models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    This is typically called during application startup or migrations.
    Uses checkfirst=True to avoid errors if tables already exist.
    """
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        # Log error but don't crash - tables might already exist
        logger.warning("Database initialization warning (this is usually safe): %s", e)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Event listener to set SQLite pragmas if using SQLite for testing.
    This is only executed when connecting to SQLite databases.
    """
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
