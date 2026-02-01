"""Add release_artifacts table for per-platform binary metadata.

Revision ID: 060_add_release_artifacts
Revises: 059_audit_team_user_rel
Create Date: 2026-02-01

Issue #136: Agent Setup Wizard — new child table for ReleaseManifest
storing per-platform artifact metadata (filename, checksum, file_size).
"""
from alembic import op
import sqlalchemy as sa

revision = '060_add_release_artifacts'
down_revision = '059_audit_team_user_rel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'release_artifacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('manifest_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('checksum', sa.String(73), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['manifest_id'], ['release_manifests.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('manifest_id', 'platform', name='uq_artifact_manifest_platform'),
    )
    op.create_index('ix_release_artifacts_manifest_id', 'release_artifacts', ['manifest_id'])
    op.create_index('ix_release_artifacts_platform', 'release_artifacts', ['platform'])


def downgrade() -> None:
    op.drop_index('ix_release_artifacts_platform', table_name='release_artifacts')
    op.drop_index('ix_release_artifacts_manifest_id', table_name='release_artifacts')
    op.drop_table('release_artifacts')
