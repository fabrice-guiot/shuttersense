"""Create jobs table with agent routing support

Revision ID: 034_create_jobs
Revises: 033_create_agent_tokens
Create Date: 2026-01-18

Creates the jobs table for persistent job queue with agent routing.
Part of Issue #90 - Distributed Agent Architecture.

This replaces the in-memory job queue with a persistent PostgreSQL-based queue.
The table supports:
- Job binding to specific agents (for LOCAL collections)
- Capability-based job routing (for remote collections)
- Job scheduling (for auto-refresh)
- Progress tracking during execution
- Result attestation (signing secret)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '034_create_jobs'
down_revision = '033_create_agent_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create jobs table with full agent routing support.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: job_xxx)
    - team_id: Owning team (FK to teams)
    - collection_id: Collection being analyzed (FK to collections, nullable for display_graph mode)
    - pipeline_id: Pipeline used (FK to pipelines, nullable)
    - pipeline_version: Pipeline version at execution time
    - tool: Analysis tool (photostats, photo_pairing, pipeline_validation)
    - mode: Execution mode (e.g., 'collection', 'display_graph')
    - status: Job status (scheduled, pending, assigned, running, completed, failed, cancelled)
    - priority: Job priority (higher = more urgent, default 0)
    - bound_agent_id: Required agent for LOCAL collections (FK to agents)
    - required_capabilities_json: Capabilities needed for unbound jobs
    - agent_id: Currently assigned/executing agent (FK to agents)
    - assigned_at: When job was assigned to agent
    - started_at: When job execution began
    - completed_at: When job finished
    - progress_json: Current progress data (stage, percentage, files)
    - error_message: Error message if failed
    - retry_count: Number of retry attempts
    - max_retries: Maximum retries allowed (default 3)
    - scheduled_for: Earliest execution time (NULL = immediate)
    - parent_job_id: Previous job in refresh chain (self-ref FK)
    - signing_secret_hash: For HMAC result verification
    - result_id: Associated analysis result (FK to analysis_results)
    - created_at/updated_at: Timestamps
    """
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('collection_id', sa.Integer(), nullable=True),  # Nullable for display_graph mode
        sa.Column('pipeline_id', sa.Integer(), nullable=True),
        sa.Column('pipeline_version', sa.Integer(), nullable=True),
        sa.Column('tool', sa.String(length=50), nullable=False),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bound_agent_id', sa.Integer(), nullable=True),
        sa.Column(
            'required_capabilities_json',
            postgresql.JSONB().with_variant(sa.Text(), 'sqlite'),
            nullable=False,
            server_default='[]'
        ),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column(
            'progress_json',
            postgresql.JSONB().with_variant(sa.Text(), 'sqlite'),
            nullable=True
        ),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('parent_job_id', sa.Integer(), nullable=True),
        sa.Column('signing_secret_hash', sa.String(length=64), nullable=True),
        sa.Column('result_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['team_id'],
            ['teams.id'],
            name='fk_jobs_team_id'
        ),
        sa.ForeignKeyConstraint(
            ['collection_id'],
            ['collections.id'],
            name='fk_jobs_collection_id',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['pipeline_id'],
            ['pipelines.id'],
            name='fk_jobs_pipeline_id',
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['bound_agent_id'],
            ['agents.id'],
            name='fk_jobs_bound_agent_id'
        ),
        sa.ForeignKeyConstraint(
            ['agent_id'],
            ['agents.id'],
            name='fk_jobs_agent_id'
        ),
        sa.ForeignKeyConstraint(
            ['parent_job_id'],
            ['jobs.id'],
            name='fk_jobs_parent_job_id'
        ),
        sa.ForeignKeyConstraint(
            ['result_id'],
            ['analysis_results.id'],
            name='fk_jobs_result_id',
            ondelete='SET NULL'
        ),
        sa.UniqueConstraint('uuid')
    )

    # Create indexes
    op.create_index('ix_jobs_uuid', 'jobs', ['uuid'], unique=True)
    op.create_index('ix_jobs_team_id', 'jobs', ['team_id'])
    op.create_index('ix_jobs_collection_id', 'jobs', ['collection_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_bound_agent_id', 'jobs', ['bound_agent_id'])
    op.create_index('ix_jobs_agent_id', 'jobs', ['agent_id'])
    op.create_index('ix_jobs_scheduled_for', 'jobs', ['scheduled_for'])

    # Composite index for job claiming query
    op.create_index(
        'ix_jobs_claimable',
        'jobs',
        ['team_id', 'status', 'scheduled_for', 'priority']
    )

    # Create partial unique index for scheduled jobs (one scheduled job per collection+tool)
    # Note: This syntax works for PostgreSQL; SQLite doesn't support partial unique indexes
    # For SQLite tests, we handle uniqueness in application code
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_scheduled_per_collection
        ON jobs (collection_id, tool)
        WHERE status = 'scheduled'
        """
    )


def downgrade() -> None:
    """Drop jobs table."""
    # Drop the partial unique index
    op.execute("DROP INDEX IF EXISTS uq_jobs_scheduled_per_collection")

    # Drop indexes
    op.drop_index('ix_jobs_claimable', table_name='jobs')
    op.drop_index('ix_jobs_scheduled_for', table_name='jobs')
    op.drop_index('ix_jobs_agent_id', table_name='jobs')
    op.drop_index('ix_jobs_bound_agent_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_collection_id', table_name='jobs')
    op.drop_index('ix_jobs_team_id', table_name='jobs')
    op.drop_index('ix_jobs_uuid', table_name='jobs')
    op.drop_table('jobs')
