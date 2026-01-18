"""Create agents table

Revision ID: 032_create_agents
Revises: 031_populate_team_id_not_null
Create Date: 2026-01-18

Creates the agents table for distributed agent architecture.
Part of Issue #90 - Distributed Agent Architecture.

Agents are worker processes running on user-owned hardware that execute
analysis jobs. Each agent belongs to a team and has a dedicated SYSTEM user
for audit trail purposes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '032_create_agents'
down_revision = '031_team_id_not_null'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create agents table.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: agt_xxx)
    - team_id: Owning team (FK to teams)
    - system_user_id: Dedicated SYSTEM user for audit (FK to users)
    - created_by_user_id: Human who registered agent (FK to users)
    - name: User-friendly agent name
    - hostname: Machine hostname (auto-detected)
    - os_info: OS type/version
    - status: Agent status (online/offline/error/revoked)
    - error_message: Last error if status=error
    - last_heartbeat: Last successful heartbeat timestamp
    - capabilities_json: Declared capabilities as JSONB
    - connectors_json: Connector GUIDs with local credentials as JSONB
    - api_key_hash: SHA-256 hash of agent API key
    - api_key_prefix: First 8 chars for identification
    - version: Agent software version
    - binary_checksum: SHA-256 of agent binary (for attestation)
    - revocation_reason: Reason if status=revoked
    - revoked_at: Timestamp of revocation
    - created_at/updated_at: Timestamps
    """
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('system_user_id', sa.Integer(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('os_info', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='offline'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column(
            'capabilities_json',
            postgresql.JSONB().with_variant(sa.Text(), 'sqlite'),
            nullable=False,
            server_default='[]'
        ),
        sa.Column(
            'connectors_json',
            postgresql.JSONB().with_variant(sa.Text(), 'sqlite'),
            nullable=False,
            server_default='[]'
        ),
        sa.Column('api_key_hash', sa.String(length=255), nullable=False),
        sa.Column('api_key_prefix', sa.String(length=10), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('binary_checksum', sa.String(length=64), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['team_id'],
            ['teams.id'],
            name='fk_agents_team_id'
        ),
        sa.ForeignKeyConstraint(
            ['system_user_id'],
            ['users.id'],
            name='fk_agents_system_user_id'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            name='fk_agents_created_by_user_id'
        ),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('api_key_hash', name='uq_agents_api_key_hash')
    )

    # Create indexes
    op.create_index('ix_agents_uuid', 'agents', ['uuid'], unique=True)
    op.create_index('ix_agents_team_id', 'agents', ['team_id'])
    op.create_index('ix_agents_status', 'agents', ['status'])
    op.create_index('ix_agents_api_key_prefix', 'agents', ['api_key_prefix'])


def downgrade() -> None:
    """Drop agents table."""
    op.drop_index('ix_agents_api_key_prefix', table_name='agents')
    op.drop_index('ix_agents_status', table_name='agents')
    op.drop_index('ix_agents_team_id', table_name='agents')
    op.drop_index('ix_agents_uuid', table_name='agents')
    op.drop_table('agents')
