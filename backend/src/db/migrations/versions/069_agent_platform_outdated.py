"""Add platform and is_outdated columns to agents table.

Revision ID: 069_agent_platform_outdated
Revises: 068_fix_cameras_uuid_type
Create Date: 2026-02-18

Supports agent upgrade detection (Issue #239). The platform column stores the
agent's OS/arch (e.g., 'darwin-arm64') and is_outdated flags agents whose
binary_checksum does not match the latest active release manifest.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '069_agent_platform_outdated'
down_revision = '068_fix_cameras_uuid_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add platform and is_outdated to agents."""
    op.add_column('agents', sa.Column('platform', sa.String(50), nullable=True))
    op.add_column('agents', sa.Column(
        'is_outdated', sa.Boolean(), server_default='false', nullable=False
    ))


def downgrade() -> None:
    """Remove platform and is_outdated from agents."""
    op.drop_column('agents', 'is_outdated')
    op.drop_column('agents', 'platform')
