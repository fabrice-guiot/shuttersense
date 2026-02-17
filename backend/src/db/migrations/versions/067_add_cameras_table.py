"""Create cameras table for camera equipment tracking.

Revision ID: 067_add_cameras_table
Revises: 066_seed_conflict_defaults
Create Date: 2026-02-17

Issue #217: Pipeline-Driven Analysis Tools
Creates the cameras table for tracking physical camera equipment
discovered during analysis or manually created by users.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '067_add_cameras_table'
down_revision = '066_seed_conflict_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cameras table with indexes and constraints."""
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True).with_variant(sa.LargeBinary(16), 'sqlite'), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('camera_id', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='temporary'),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('make', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('serial_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('team_id', 'camera_id', name='uq_cameras_team_camera_id'),
    )
    op.create_index('ix_cameras_uuid', 'cameras', ['uuid'])
    op.create_index('ix_cameras_team_id', 'cameras', ['team_id'])
    op.create_index('ix_cameras_status', 'cameras', ['status'])


def downgrade() -> None:
    """Drop cameras table."""
    op.drop_index('ix_cameras_status', table_name='cameras')
    op.drop_index('ix_cameras_team_id', table_name='cameras')
    op.drop_index('ix_cameras_uuid', table_name='cameras')
    op.drop_table('cameras')
