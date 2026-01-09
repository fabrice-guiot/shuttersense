"""Create analysis_results table

Revision ID: 004_analysis_results
Revises: 003_pipelines
Create Date: 2026-01-04

Creates:
- analysis_results table for storing tool execution results
- resultstatus enum for result status tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '004_analysis_results'
down_revision = '003_pipelines'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create analysis_results table.

    Stores results from PhotoStats, Photo Pairing, and Pipeline Validation
    tool executions with JSONB results and optional HTML reports.
    """

    # Create resultstatus enum
    resultstatus_enum = postgresql.ENUM(
        'COMPLETED', 'FAILED', 'CANCELLED',
        name='resultstatus',
        create_type=False
    )
    resultstatus_enum.create(op.get_bind(), checkfirst=True)

    # Create analysis_results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('pipeline_id', sa.Integer(), nullable=True),
        sa.Column('tool', sa.String(length=50), nullable=False),
        sa.Column('status', resultstatus_enum, nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('results_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('report_html', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('files_scanned', sa.Integer(), nullable=True),
        sa.Column('issues_found', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_id'], ['pipelines.id'], ondelete='SET NULL')
    )

    # Create indexes on analysis_results
    op.create_index('ix_analysis_results_collection_id', 'analysis_results', ['collection_id'], unique=False)
    op.create_index('ix_analysis_results_pipeline_id', 'analysis_results', ['pipeline_id'], unique=False)
    op.create_index('ix_analysis_results_tool', 'analysis_results', ['tool'], unique=False)
    op.create_index('ix_analysis_results_created_at', 'analysis_results', ['created_at'], unique=False)
    op.create_index(
        'ix_analysis_results_collection_tool_date',
        'analysis_results',
        ['collection_id', 'tool', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """
    Drop analysis_results table and resultstatus enum.

    Note: This will drop all analysis result data.
    """
    # Drop indexes on analysis_results
    op.drop_index('ix_analysis_results_collection_tool_date', table_name='analysis_results')
    op.drop_index('ix_analysis_results_created_at', table_name='analysis_results')
    op.drop_index('ix_analysis_results_tool', table_name='analysis_results')
    op.drop_index('ix_analysis_results_pipeline_id', table_name='analysis_results')
    op.drop_index('ix_analysis_results_collection_id', table_name='analysis_results')

    # Drop analysis_results table
    op.drop_table('analysis_results')

    # Drop resultstatus enum
    postgresql.ENUM(name='resultstatus').drop(op.get_bind(), checkfirst=True)
