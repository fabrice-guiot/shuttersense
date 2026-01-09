"""Make collection_id nullable in analysis_results

Revision ID: 008_nullable_collection_id
Revises: 007_collection_pipeline
Create Date: 2026-01-06

Allows pipeline validation results without a collection (display-graph mode).
Pipeline-only validation validates the pipeline definition without scanning a folder.

Design Notes:
- collection_id becomes nullable to support display-graph mode
- Existing results with collection_id remain unchanged
- Pipeline-only results have collection_id=NULL
- CASCADE on delete still works for results with collection_id
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_nullable_collection_id'
down_revision = '007_collection_pipeline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Make collection_id nullable in analysis_results.

    This enables storing pipeline validation results without a collection
    (display-graph mode), which validates the pipeline definition only.
    """
    op.alter_column(
        'analysis_results',
        'collection_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    """
    Make collection_id required again.

    Warning: This will fail if any rows have NULL collection_id.
    Those rows must be deleted first.
    """
    op.alter_column(
        'analysis_results',
        'collection_id',
        existing_type=sa.Integer(),
        nullable=False
    )
