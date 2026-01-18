"""
Database connection and session management.

This module provides SQLAlchemy engine configuration for PostgreSQL
with connection pooling optimized for the ShutterSense application.
"""

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool


# Load environment variables from .env file
# Look for .env in backend directory (parent of src)
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Database URL from environment variable
DATABASE_URL = os.environ.get(
    "SHUSAI_DB_URL",
    "postgresql://user:password@localhost:5432/shuttersense"
)


# SQLAlchemy engine with connection pooling
# Pool configuration based on research.md Task 8 and performance targets
# Use different parameters for SQLite vs PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support pool_size, max_overflow, or pool_recycle
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=False,
        future=True
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,          # Maximum connections in pool (from research.md)
        max_overflow=10,       # Additional connections beyond pool_size
        pool_pre_ping=True,    # Verify connections before checkout
        pool_recycle=3600,     # Recycle connections after 1 hour
        echo=False,            # Set to True for SQL debugging
        future=True            # Use SQLAlchemy 2.0 style
    )


# Session factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True  # SQLAlchemy 2.0 style
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get database session.

    Yields:
        Session: SQLAlchemy database session

    Usage:
        @app.get("/collections")
        async def list_collections(db: Session = Depends(get_db)):
            collections = db.query(Collection).all()
            return collections
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Event listeners for connection management
@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Set connection parameters on new connections.
    Currently a placeholder for PostgreSQL-specific settings.
    """
    # For PostgreSQL, we could set:
    # cursor = dbapi_conn.cursor()
    # cursor.execute("SET timezone TO 'UTC'")
    # cursor.close()
    pass


@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Log new database connections (optional).
    Useful for monitoring connection pool usage.
    """
    # Placeholder for connection logging
    # import logging
    # logger = logging.getLogger(__name__)
    # logger.debug(f"New database connection established: {connection_record}")
    pass


def init_db():
    """
    Initialize database tables.

    This should only be called during initial setup or testing.
    For production, use Alembic migrations instead.
    """
    from backend.src.models import Base
    Base.metadata.create_all(bind=engine)


def dispose_engine():
    """
    Dispose of the engine and close all connections.

    Useful for cleanup in CLI tools and tests.
    """
    engine.dispose()
