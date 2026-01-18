"""Add credential_location to connectors

Revision ID: 035_connector_cred_loc
Revises: 034_enhance_jobs
Create Date: 2026-01-18

Adds credential_location field to connectors table.
Part of Issue #90 - Distributed Agent Architecture.

The credential_location field specifies where connector credentials are stored:
- SERVER: Encrypted on server (current behavior, default for existing connectors)
- AGENT: Only on agent(s), NOT on server
- PENDING: No credentials yet, awaiting configuration
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035_connector_cred_loc'
down_revision = '034_create_jobs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add credential_location column to connectors table.

    New column:
    - credential_location: Where credentials are stored (server/agent/pending)

    Default value 'server' maintains backward compatibility with existing connectors.
    """
    op.add_column(
        'connectors',
        sa.Column(
            'credential_location',
            sa.String(length=20),
            nullable=False,
            server_default='server'
        )
    )

    # Create index for filtering by credential location
    op.create_index('ix_connectors_credential_location', 'connectors', ['credential_location'])


def downgrade() -> None:
    """Remove credential_location from connectors table."""
    op.drop_index('ix_connectors_credential_location', table_name='connectors')
    op.drop_column('connectors', 'credential_location')
