"""Add is_mappable column to inventory_folders.

Tracks whether a folder is still eligible for mapping to a collection.
A folder is NOT mappable if:
1. It is directly mapped (collection_guid is set), OR
2. An ancestor folder is mapped, OR
3. A descendant folder is mapped

Revision ID: 056_add_folder_is_mappable
Revises: 055_add_connector_id_to_results
Create Date: 2026-01-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "056_add_folder_is_mappable"
down_revision = "055_add_connector_id_to_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_mappable column with default True."""
    op.add_column(
        "inventory_folders",
        sa.Column("is_mappable", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Remove is_mappable column."""
    op.drop_column("inventory_folders", "is_mappable")
