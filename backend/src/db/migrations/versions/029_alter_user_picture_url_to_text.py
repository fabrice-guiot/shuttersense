"""Alter users.picture_url from String(1024) to Text

Revision ID: 029_alter_picture_url
Revises: 028_add_team_id_to_existing_tables
Create Date: 2026-01-16

Changes picture_url column to Text to support base64-encoded data URLs
from Microsoft Graph API profile photos (which can be 50KB+).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '029_alter_picture_url'
down_revision = '028_add_team_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change picture_url from String(1024) to Text for base64 data URLs."""
    # PostgreSQL: ALTER COLUMN TYPE
    # SQLite: Alembic handles this with batch operations
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'picture_url',
            existing_type=sa.String(length=1024),
            type_=sa.Text(),
            existing_nullable=True
        )


def downgrade() -> None:
    """Revert picture_url to String(1024) - may truncate data."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'picture_url',
            existing_type=sa.Text(),
            type_=sa.String(length=1024),
            existing_nullable=True
        )
