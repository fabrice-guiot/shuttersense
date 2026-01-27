"""Add inventory_latest_manifest column to connectors.

Revision ID: 054_add_inventory_latest_manifest
Revises: 053_inventory_import_tables
Create Date: 2026-01-27

Issue #107: Cloud Storage Bucket Inventory Import
- Track the path of the latest detected manifest.json file
- Helps users understand which inventory snapshot will be imported
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '054_add_inventory_latest_manifest'
down_revision = '053_inventory_import_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add inventory_latest_manifest column to connectors."""
    op.add_column('connectors', sa.Column(
        'inventory_latest_manifest',
        sa.String(500),
        nullable=True,
        comment='Latest detected manifest path (e.g., 2026-01-26T01-00Z/manifest.json)'
    ))


def downgrade() -> None:
    """Remove inventory_latest_manifest column from connectors."""
    op.drop_column('connectors', 'inventory_latest_manifest')
