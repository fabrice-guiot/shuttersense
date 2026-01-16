"""Create api_tokens table

Revision ID: 027_create_api_tokens_table
Revises: 026_create_users_table
Create Date: 2026-01-15

Creates the api_tokens table for programmatic API access.
Part of Issue #73 - Teams/Tenants and User Management.

API tokens are JWT-based credentials for automation and integrations.
The token hash is stored for revocation lookup, while the full token
is only shown once at creation time.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '027_create_api_tokens'
down_revision = '026_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create api_tokens table.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: tok_xxx)
    - user_id: Token owner (FK to users)
    - team_id: Team scope (denormalized from user for query efficiency)
    - name: User-provided token name/description
    - token_hash: SHA-256 hash of the full JWT (for validation)
    - token_prefix: First 8 characters of token (for UI identification)
    - scopes_json: Allowed API scopes as JSON array
    - expires_at: Token expiration timestamp
    - last_used_at: Last API call using this token
    - is_active: Token active status (for revocation)
    - created_at: Creation timestamp
    """
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('token_prefix', sa.String(length=10), nullable=False),
        sa.Column('scopes_json', sa.Text(), nullable=False, server_default='["*"]'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_api_tokens_user_id'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name='fk_api_tokens_team_id'),
        sa.UniqueConstraint('token_hash'),
        sa.UniqueConstraint('uuid')
    )

    # Create indexes
    op.create_index('ix_api_tokens_uuid', 'api_tokens', ['uuid'], unique=True)
    op.create_index('ix_api_tokens_token_hash', 'api_tokens', ['token_hash'], unique=True)
    op.create_index('ix_api_tokens_user_id', 'api_tokens', ['user_id'])
    op.create_index('ix_api_tokens_team_id', 'api_tokens', ['team_id'])
    op.create_index('ix_api_tokens_expires_at', 'api_tokens', ['expires_at'])
    op.create_index('ix_api_tokens_is_active', 'api_tokens', ['is_active'])


def downgrade() -> None:
    """Drop api_tokens table."""
    op.drop_index('ix_api_tokens_is_active', table_name='api_tokens')
    op.drop_index('ix_api_tokens_expires_at', table_name='api_tokens')
    op.drop_index('ix_api_tokens_team_id', table_name='api_tokens')
    op.drop_index('ix_api_tokens_user_id', table_name='api_tokens')
    op.drop_index('ix_api_tokens_token_hash', table_name='api_tokens')
    op.drop_index('ix_api_tokens_uuid', table_name='api_tokens')
    op.drop_table('api_tokens')
