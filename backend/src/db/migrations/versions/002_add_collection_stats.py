"""Add collection stats columns for KPI aggregation

Revision ID: 002_add_collection_stats
Revises: 001_initial_collections
Create Date: 2026-01-03

Adds storage_bytes, file_count, and image_count columns to collections table
for KPI aggregation (Issue #37). These columns are nullable and populated
during collection scan/refresh operations.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_collection_stats'
down_revision = '001_initial_collections'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add stats columns to collections table.

    Columns:
    - storage_bytes: Total storage used in bytes (BigInteger for >2GB)
    - file_count: Total number of files in collection
    - image_count: Number of images after grouping
    """
    op.add_column('collections', sa.Column('storage_bytes', sa.BigInteger(), nullable=True))
    op.add_column('collections', sa.Column('file_count', sa.Integer(), nullable=True))
    op.add_column('collections', sa.Column('image_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    """
    Remove stats columns from collections table.
    """
    op.drop_column('collections', 'image_count')
    op.drop_column('collections', 'file_count')
    op.drop_column('collections', 'storage_bytes')
