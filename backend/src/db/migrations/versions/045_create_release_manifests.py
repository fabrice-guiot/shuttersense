"""Create release_manifests table for agent attestation.

Revision ID: 045_create_release_manifests
Revises: 044_rm_coll_refresh_fields
Create Date: 2026-01-21

Stores known-good checksums for released agent binaries.
During registration, an agent's checksum is validated against this table.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '045_create_release_manifests'
down_revision = '044_rm_coll_refresh_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create release_manifests table."""
    op.create_table(
        'release_manifests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.LargeBinary(length=16), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes
    op.create_index('ix_release_manifests_uuid', 'release_manifests', ['uuid'], unique=True)
    op.create_index('ix_release_manifests_version', 'release_manifests', ['version'])
    op.create_index('ix_release_manifests_platform', 'release_manifests', ['platform'])
    op.create_index('ix_release_manifests_checksum', 'release_manifests', ['checksum'])
    op.create_index('ix_release_manifests_is_active', 'release_manifests', ['is_active'])
    op.create_index('uq_release_version_platform', 'release_manifests', ['version', 'platform'], unique=True)


def downgrade() -> None:
    """Drop release_manifests table."""
    op.drop_index('uq_release_version_platform', table_name='release_manifests')
    op.drop_index('ix_release_manifests_is_active', table_name='release_manifests')
    op.drop_index('ix_release_manifests_checksum', table_name='release_manifests')
    op.drop_index('ix_release_manifests_platform', table_name='release_manifests')
    op.drop_index('ix_release_manifests_version', table_name='release_manifests')
    op.drop_index('ix_release_manifests_uuid', table_name='release_manifests')
    op.drop_table('release_manifests')
