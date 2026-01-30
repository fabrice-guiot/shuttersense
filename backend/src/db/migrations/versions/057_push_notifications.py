"""Add push notification tables.

Revision ID: 057_push_notifications
Revises: 056_add_folder_is_mappable
Create Date: 2026-01-30

Issue #114: PWA with Push Notifications
- Create push_subscriptions table for Web Push subscription storage
- Create notifications table for notification history
- Add partial index for efficient unread count queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '057_push_notifications'
down_revision = '056_add_folder_is_mappable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add push_subscriptions and notifications tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # =========================================================================
    # Create push_subscriptions table
    # =========================================================================
    if dialect == 'postgresql':
        op.create_table(
            'push_subscriptions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', name='fk_push_subscriptions_team_id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_push_subscriptions_user_id'), nullable=False),
            sa.Column('endpoint', sa.String(1024), nullable=False, unique=True),
            sa.Column('p256dh_key', sa.String(255), nullable=False),
            sa.Column('auth_key', sa.String(255), nullable=False),
            sa.Column('device_name', sa.String(100), nullable=True),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        )
    else:
        # SQLite: use LargeBinary for UUID
        op.create_table(
            'push_subscriptions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', sa.LargeBinary(16), nullable=False, unique=True, index=True),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', name='fk_push_subscriptions_team_id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_push_subscriptions_user_id'), nullable=False),
            sa.Column('endpoint', sa.String(1024), nullable=False, unique=True),
            sa.Column('p256dh_key', sa.String(255), nullable=False),
            sa.Column('auth_key', sa.String(255), nullable=False),
            sa.Column('device_name', sa.String(100), nullable=True),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("datetime('now')")),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("datetime('now')")),
        )

    # Indexes for push_subscriptions
    op.create_index('ix_push_subscriptions_team_id', 'push_subscriptions', ['team_id'])
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])

    # =========================================================================
    # Create notifications table
    # =========================================================================
    if dialect == 'postgresql':
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', name='fk_notifications_team_id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_notifications_user_id'), nullable=False),
            sa.Column('category', sa.String(30), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('body', sa.String(500), nullable=False),
            sa.Column('data', postgresql.JSONB(), nullable=True),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), index=True),
        )
    else:
        # SQLite: use LargeBinary for UUID, JSON for data
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', sa.LargeBinary(16), nullable=False, unique=True, index=True),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', name='fk_notifications_team_id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_notifications_user_id'), nullable=False),
            sa.Column('category', sa.String(30), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('body', sa.String(500), nullable=False),
            sa.Column('data', sa.JSON(), nullable=True),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("datetime('now')"), index=True),
        )

    # Indexes for notifications
    op.create_index('ix_notifications_team_id', 'notifications', ['team_id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])

    # Partial index for unread notifications (PostgreSQL only)
    if dialect == 'postgresql':
        op.create_index(
            'ix_notifications_user_unread',
            'notifications',
            ['user_id'],
            postgresql_where=sa.text('read_at IS NULL'),
        )


def downgrade() -> None:
    """Remove push notification tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Drop notifications indexes and table
    if dialect == 'postgresql':
        op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_team_id', table_name='notifications')
    op.drop_table('notifications')

    # Drop push_subscriptions indexes and table
    op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_team_id', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
