"""Add is_default column to pipelines table

Revision ID: 006_add_pipeline_is_default
Revises: 005_configurations
Create Date: 2026-01-06

Adds:
- is_default column to distinguish between active (ready for use) and default (used by tools)
- Index on is_default for efficient lookup
- Migrates existing active pipeline to default (backwards compatibility)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_pipeline_is_default'
down_revision = '005_configurations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add is_default column to pipelines table.

    The is_default column distinguishes between:
    - is_active: Pipeline is valid and ready for use (multiple can be active)
    - is_default: Pipeline is used by tools for execution (only one can be default)

    For backwards compatibility, if there's a single active pipeline, it becomes the default.
    """
    # Add is_default column with default=False
    op.add_column(
        'pipelines',
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false')
    )

    # Create index on is_default
    op.create_index('ix_pipelines_is_default', 'pipelines', ['is_default'], unique=False)

    # Migrate: Set the first active pipeline as default (if any)
    # This maintains backwards compatibility where the active pipeline was used by tools
    op.execute("""
        UPDATE pipelines
        SET is_default = true
        WHERE id = (
            SELECT id FROM pipelines
            WHERE is_active = true
            ORDER BY id
            LIMIT 1
        )
    """)


def downgrade() -> None:
    """
    Remove is_default column from pipelines table.

    Note: This will lose the distinction between active and default pipelines.
    """
    # Drop index on is_default
    op.drop_index('ix_pipelines_is_default', table_name='pipelines')

    # Drop is_default column
    op.drop_column('pipelines', 'is_default')
