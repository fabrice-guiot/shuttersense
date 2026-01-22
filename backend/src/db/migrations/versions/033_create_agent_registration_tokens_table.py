"""Create agent_registration_tokens table

Revision ID: 033_create_agent_tokens
Revises: 032_create_agents
Create Date: 2026-01-18

Creates the agent_registration_tokens table for one-time agent registration.
Part of Issue #90 - Distributed Agent Architecture.

Registration tokens are single-use tokens that allow agents to register
with a ShutterSense server. They expire after 24 hours by default.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '033_create_agent_tokens'
down_revision = '032_create_agents'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create agent_registration_tokens table.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: art_xxx)
    - team_id: Team this token registers for (FK to teams)
    - created_by_user_id: User who created the token (FK to users)
    - token_hash: SHA-256 hash of the token
    - name: Optional description for the token
    - is_used: Whether the token has been used
    - used_by_agent_id: Agent that used this token (FK to agents)
    - expires_at: Token expiration timestamp
    - created_at: Creation timestamp
    """
    op.create_table(
        'agent_registration_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_by_agent_id', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['team_id'],
            ['teams.id'],
            name='fk_art_team_id'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            name='fk_art_created_by_user_id'
        ),
        sa.ForeignKeyConstraint(
            ['used_by_agent_id'],
            ['agents.id'],
            name='fk_art_used_by_agent_id'
        ),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('token_hash', name='uq_art_token_hash')
    )

    # Create indexes
    op.create_index('ix_art_uuid', 'agent_registration_tokens', ['uuid'], unique=True)
    op.create_index(
        'ix_art_team_expires',
        'agent_registration_tokens',
        ['team_id', 'expires_at', 'is_used']
    )


def downgrade() -> None:
    """Drop agent_registration_tokens table."""
    op.drop_index('ix_art_team_expires', table_name='agent_registration_tokens')
    op.drop_index('ix_art_uuid', table_name='agent_registration_tokens')
    op.drop_table('agent_registration_tokens')
