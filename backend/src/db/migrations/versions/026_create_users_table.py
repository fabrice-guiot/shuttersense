"""Create users table

Revision ID: 026_create_users_table
Revises: 025_create_teams_table
Create Date: 2026-01-15

Creates the users table for authenticated user management.
Part of Issue #73 - Teams/Tenants and User Management.

Users are pre-provisioned by team administrators before they can
log in via OAuth. Each user belongs to exactly one team.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '026_create_users'
down_revision = '025_create_teams'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create users table.

    Columns:
    - id: Primary key (internal)
    - uuid: UUIDv7 for external identification (GUID: usr_xxx)
    - team_id: Team membership (FK to teams)
    - email: Login email (globally unique across ALL teams)
    - first_name/last_name: User name (from invite or OAuth)
    - display_name: Display name (OAuth sync or manual)
    - picture_url: Profile picture URL (from OAuth)
    - is_active: Account active status (controls login)
    - status: Account lifecycle status (pending/active/deactivated)
    - last_login_at: Last successful login timestamp
    - oauth_provider: Last used OAuth provider
    - oauth_subject: OAuth sub claim for identity verification
    - preferences_json: User preferences as JSON
    - created_at/updated_at: Timestamps
    """
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            'uuid',
            postgresql.UUID(as_uuid=True).with_variant(
                sa.LargeBinary(16), 'sqlite'
            ),
            nullable=False
        ),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('picture_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('oauth_provider', sa.String(length=50), nullable=True),
        sa.Column('oauth_subject', sa.String(length=255), nullable=True),
        sa.Column('preferences_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], name='fk_users_team_id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('uuid')
    )

    # Create indexes
    op.create_index('ix_users_uuid', 'users', ['uuid'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_team_id', 'users', ['team_id'])
    op.create_index('ix_users_status', 'users', ['status'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_oauth_subject', 'users', ['oauth_subject'])


def downgrade() -> None:
    """Drop users table."""
    op.drop_index('ix_users_oauth_subject', table_name='users')
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_status', table_name='users')
    op.drop_index('ix_users_team_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_uuid', table_name='users')
    op.drop_table('users')
