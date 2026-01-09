"""Add pipeline integration to collections and version to analysis_results

Revision ID: 007_collection_pipeline
Revises: 006_add_pipeline_is_default
Create Date: 2026-01-06

Adds:
- pipeline_id and pipeline_version columns to collections table for explicit pipeline assignment
- pipeline_version column to analysis_results table to capture version used at execution time

Design Notes:
- Collections can optionally have an explicit pipeline+version assignment
- If not assigned, collections use the default pipeline at runtime
- AnalysisResult stores the exact pipeline+version used during tool execution
- PhotoStats/PhotoPairing can run without a pipeline (NULL values)
- Pipeline Validation requires a valid pipeline+version
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_collection_pipeline'
down_revision = '006_add_pipeline_is_default'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add pipeline integration columns.

    Collections:
    - pipeline_id: Foreign key to pipelines table (SET NULL on delete)
    - pipeline_version: Version number pinned at assignment time

    Analysis Results:
    - pipeline_version: Version number used during execution (complements existing pipeline_id)
    """
    # Add pipeline_id column to collections
    op.add_column(
        'collections',
        sa.Column('pipeline_id', sa.Integer(), nullable=True)
    )

    # Add pipeline_version column to collections
    op.add_column(
        'collections',
        sa.Column('pipeline_version', sa.Integer(), nullable=True)
    )

    # Create foreign key constraint for collections.pipeline_id
    op.create_foreign_key(
        'fk_collections_pipeline_id',
        'collections',
        'pipelines',
        ['pipeline_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index on collections.pipeline_id
    op.create_index(
        'ix_collections_pipeline_id',
        'collections',
        ['pipeline_id'],
        unique=False
    )

    # Add pipeline_version column to analysis_results
    op.add_column(
        'analysis_results',
        sa.Column('pipeline_version', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """
    Remove pipeline integration columns.
    """
    # Drop pipeline_version from analysis_results
    op.drop_column('analysis_results', 'pipeline_version')

    # Drop index on collections.pipeline_id
    op.drop_index('ix_collections_pipeline_id', table_name='collections')

    # Drop foreign key constraint
    op.drop_constraint('fk_collections_pipeline_id', 'collections', type_='foreignkey')

    # Drop pipeline_version from collections
    op.drop_column('collections', 'pipeline_version')

    # Drop pipeline_id from collections
    op.drop_column('collections', 'pipeline_id')
