"""Add connector_id column to analysis_results.

Revision ID: 055_add_connector_id_to_results
Revises: 054_add_latest_manifest
Create Date: 2026-01-27

Issue #107: Cloud Storage Bucket Inventory Import
- Add connector_id FK to AnalysisResult for inventory tools
- Inventory validation and import results link to the connector, not a collection
- Follows the polymorphic results pattern planned in domain-model.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '055_add_connector_id_to_results'
down_revision = '054_add_latest_manifest'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add connector_id column to analysis_results with FK and index."""
    # Add the column
    op.add_column('analysis_results', sa.Column(
        'connector_id',
        sa.Integer(),
        nullable=True,
        comment='Connector FK for inventory tools (Issue #107)'
    ))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_analysis_results_connector_id',
        'analysis_results',
        'connectors',
        ['connector_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add index for efficient lookups
    op.create_index(
        'idx_results_connector',
        'analysis_results',
        ['connector_id']
    )


def downgrade() -> None:
    """Remove connector_id column from analysis_results."""
    # Drop index
    op.drop_index('idx_results_connector', table_name='analysis_results')

    # Drop foreign key
    op.drop_constraint(
        'fk_analysis_results_connector_id',
        'analysis_results',
        type_='foreignkey'
    )

    # Drop column
    op.drop_column('analysis_results', 'connector_id')
