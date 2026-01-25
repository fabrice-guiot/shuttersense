"""
Custom SQLAlchemy types for cross-database compatibility.

Provides types that work across PostgreSQL and SQLite for testing.
"""

from sqlalchemy import TypeDecorator, JSON
from sqlalchemy.dialects.postgresql import JSONB


class JSONBType(TypeDecorator):
    """
    Platform-independent JSONB type.

    Uses PostgreSQL's native JSONB type when available,
    otherwise falls back to JSON for SQLite.

    This allows tests to run on SQLite while production
    uses PostgreSQL's more efficient JSONB type.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())
