"""Fix cameras.uuid column type from bytea to native UUID on PostgreSQL.

Revision ID: 068_fix_cameras_uuid_type
Revises: 067_add_cameras_table
Create Date: 2026-02-17

Migration 067 created the uuid column as LargeBinary(16) which maps to
bytea on PostgreSQL. The GuidMixin UUIDType expects native PostgreSQL UUID.
This migration drops and re-adds the column with the correct type.
The cameras table should be empty since inserts failed due to this mismatch.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '068_fix_cameras_uuid_type'
down_revision = '067_add_cameras_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace cameras.uuid bytea column with native UUID type on PostgreSQL."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Drop the existing indexes and constraints on the bytea uuid column
        op.drop_index('ix_cameras_uuid', table_name='cameras')
        op.drop_constraint('cameras_uuid_key', 'cameras', type_='unique')
        op.drop_column('cameras', 'uuid')

        # Re-add with correct type
        op.add_column(
            'cameras',
            sa.Column(
                'uuid',
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
        )
        op.create_unique_constraint('cameras_uuid_key', 'cameras', ['uuid'])
        op.create_index('ix_cameras_uuid', 'cameras', ['uuid'])


def downgrade() -> None:
    """Revert cameras.uuid back to bytea."""
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.drop_index('ix_cameras_uuid', table_name='cameras')
        op.drop_constraint('cameras_uuid_key', 'cameras', type_='unique')
        op.drop_column('cameras', 'uuid')

        op.add_column(
            'cameras',
            sa.Column('uuid', sa.LargeBinary(16), nullable=False),
        )
        op.create_unique_constraint('cameras_uuid_key', 'cameras', ['uuid'])
        op.create_index('ix_cameras_uuid', 'cameras', ['uuid'])
