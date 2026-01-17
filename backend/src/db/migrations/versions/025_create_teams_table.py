"""Create teams table

Revision ID: 025_create_teams_table
Revises: 024_add_parent_event_id_to_events
Create Date: 2026-01-15

Creates the teams table for multi-tenancy support.
Part of Issue #73 - Teams/Tenants and User Management.

Teams represent tenancy boundaries - all data in the system
belongs to exactly one Team for complete data isolation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '025_create_teams'
down_revision = '024_parent_event_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create teams table.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: ten_xxx)
    - name: Team display name (unique)
    - slug: URL-safe identifier (auto-generated from name)
    - is_active: Whether team is active (controls member login)
    - settings_json: Team-level settings as JSON
    - created_at/updated_at: Timestamps
    """
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('settings_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('uuid')
    )

    # Create indexes
    op.create_index('ix_teams_uuid', 'teams', ['uuid'], unique=True)
    op.create_index('ix_teams_name', 'teams', ['name'], unique=True)
    op.create_index('ix_teams_slug', 'teams', ['slug'], unique=True)
    op.create_index('ix_teams_is_active', 'teams', ['is_active'])


def downgrade() -> None:
    """Drop teams table."""
    op.drop_index('ix_teams_is_active', table_name='teams')
    op.drop_index('ix_teams_slug', table_name='teams')
    op.drop_index('ix_teams_name', table_name='teams')
    op.drop_index('ix_teams_uuid', table_name='teams')
    op.drop_table('teams')
