"""Add UUID columns to all user-facing entities

Revision ID: 010_add_uuid_columns
Revises: 009_add_jsonb_gin_index
Create Date: 2026-01-09

Adds UUIDv7 columns to collections, connectors, pipelines, and analysis_results
tables for external identification. This is part of Issue #42.

Migration Strategy:
1. Add nullable UUID columns to all tables
2. Populate existing records with UUIDv7 values
3. Make columns non-nullable and create unique indexes

The UUID column enables external IDs in the format {prefix}_{base32_uuid}
for URL-safe, shareable entity references.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid_extensions import uuid7


# revision identifiers, used by Alembic.
revision = '010_add_uuid_columns'
down_revision = '009_add_jsonb_gin_index'
branch_labels = None
depends_on = None


# Tables to add UUID columns to
TABLES = ['collections', 'connectors', 'pipelines', 'analysis_results']


def upgrade() -> None:
    """
    Add UUID columns to all user-facing entity tables.

    Steps:
    1. Add nullable UUID column to each table
    2. Generate UUIDv7 for all existing records
    3. Make UUID column NOT NULL
    4. Create unique index for fast lookups
    """
    conn = op.get_bind()

    for table_name in TABLES:
        # Step 1: Add nullable UUID column
        # Use postgresql.UUID for PostgreSQL, fall back to LargeBinary for SQLite
        op.add_column(
            table_name,
            sa.Column(
                'uuid',
                postgresql.UUID(as_uuid=True).with_variant(
                    sa.LargeBinary(16), 'sqlite'
                ),
                nullable=True
            )
        )

        # Step 2: Populate existing records with UUIDv7
        _populate_uuids(conn, table_name)

        # Step 3: Make column NOT NULL
        op.alter_column(
            table_name,
            'uuid',
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False
        )

        # Step 4: Create unique index for fast lookups
        op.create_index(
            f'ix_{table_name}_uuid',
            table_name,
            ['uuid'],
            unique=True
        )


def downgrade() -> None:
    """
    Remove UUID columns from all entity tables.

    Drops indexes first, then columns.
    """
    # Process in reverse order for clean rollback
    for table_name in reversed(TABLES):
        # Drop the index first
        op.drop_index(f'ix_{table_name}_uuid', table_name=table_name)
        # Drop the column
        op.drop_column(table_name, 'uuid')


def _populate_uuids(conn, table_name: str) -> None:
    """
    Generate UUIDv7 values for all existing records in a table.

    This function runs as part of the migration to ensure all existing
    records have UUIDs before the NOT NULL constraint is applied.

    Args:
        conn: Database connection from Alembic
        table_name: Name of the table to update
    """
    # Get all existing record IDs
    result = conn.execute(sa.text(f"SELECT id FROM {table_name}"))
    rows = result.fetchall()

    if not rows:
        return  # No records to update

    # Generate and set UUID for each record
    for (record_id,) in rows:
        new_uuid = uuid7()
        # Use parameterized query for safety
        conn.execute(
            sa.text(f"UPDATE {table_name} SET uuid = :uuid WHERE id = :id"),
            {"uuid": str(new_uuid), "id": record_id}
        )
