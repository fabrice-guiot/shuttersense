"""Create pipelines and pipeline_history tables

Revision ID: 003_pipelines
Revises: 002_add_collection_stats
Create Date: 2026-01-04

Creates:
- pipelines table for workflow definitions with JSONB nodes/edges
- pipeline_history table for version tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '003_pipelines'
down_revision = '002_add_collection_stats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create pipelines and pipeline_history tables.

    Tables:
    - pipelines: Workflow definitions with graph structure
    - pipeline_history: Version snapshots for audit trail
    """

    # Create pipelines table
    op.create_table(
        'pipelines',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('nodes_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('edges_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes on pipelines
    op.create_index('ix_pipelines_name', 'pipelines', ['name'], unique=True)
    op.create_index('ix_pipelines_is_active', 'pipelines', ['is_active'], unique=False)

    # Create pipeline_history table
    op.create_table(
        'pipeline_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pipeline_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('nodes_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('edges_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('changed_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='CASCADE')
    )

    # Create indexes on pipeline_history
    op.create_index('ix_pipeline_history_pipeline_id', 'pipeline_history', ['pipeline_id'], unique=False)
    op.create_index(
        'uq_pipeline_history_pipeline_version',
        'pipeline_history',
        ['pipeline_id', 'version'],
        unique=True
    )


def downgrade() -> None:
    """
    Drop pipelines and pipeline_history tables.

    Note: This will drop all pipeline data and history.
    """
    # Drop indexes on pipeline_history
    op.drop_index('uq_pipeline_history_pipeline_version', table_name='pipeline_history')
    op.drop_index('ix_pipeline_history_pipeline_id', table_name='pipeline_history')

    # Drop pipeline_history table
    op.drop_table('pipeline_history')

    # Drop indexes on pipelines
    op.drop_index('ix_pipelines_is_active', table_name='pipelines')
    op.drop_index('ix_pipelines_name', table_name='pipelines')

    # Drop pipelines table
    op.drop_table('pipelines')
