"""Add is_verified column to agents table.

Revision ID: 073_agent_is_verified
Revises: 072_polymorphic_target
Create Date: 2026-02-20

Issue #236: Continuous agent attestation enforcement.
Agents with unverified binaries can heartbeat but are blocked
from job operations (claim, complete, upload, etc.).
"""

from alembic import op
import sqlalchemy as sa

revision = '073_agent_is_verified'
down_revision = '072_polymorphic_target'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'agents',
        sa.Column(
            'is_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )


def downgrade():
    op.drop_column('agents', 'is_verified')
