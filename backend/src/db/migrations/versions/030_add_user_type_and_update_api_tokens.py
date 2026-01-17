"""Add user_type to users and update api_tokens for system users

Revision ID: 030_user_type_api_tokens
Revises: 029_alter_picture_url
Create Date: 2026-01-16

Phase 10: System User model changes for API tokens.

Changes:
1. Add user_type column to users table (human/system)
2. Rename user_id to system_user_id in api_tokens table
3. Add created_by_user_id column to api_tokens table

Design rationale:
- API tokens are now associated with system users (not human users)
- System users are auto-created when tokens are generated
- This prevents token breakage when human users are deactivated
- created_by_user_id tracks which human created the token (audit trail)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '030_user_type_api_tokens'
down_revision = '029_alter_picture_url'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add user_type to users and restructure api_tokens for system users.
    """
    # 1. Create the user_type enum type first
    user_type_enum = sa.Enum('HUMAN', 'SYSTEM', name='user_type')
    user_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add user_type column to users table
    # Default is 'HUMAN' for all existing users (uses enum member names, not values)
    op.add_column(
        'users',
        sa.Column(
            'user_type',
            user_type_enum,
            nullable=False,
            server_default='HUMAN'
        )
    )
    op.create_index('ix_users_user_type', 'users', ['user_type'])

    # 2. Rename user_id to system_user_id in api_tokens
    # First drop the old foreign key and index
    op.drop_constraint('fk_api_tokens_user_id', 'api_tokens', type_='foreignkey')
    op.drop_index('ix_api_tokens_user_id', table_name='api_tokens')

    # Rename the column
    op.alter_column('api_tokens', 'user_id', new_column_name='system_user_id')

    # Recreate foreign key and index with new names
    op.create_foreign_key(
        'fk_api_tokens_system_user_id',
        'api_tokens',
        'users',
        ['system_user_id'],
        ['id']
    )
    op.create_index('ix_api_tokens_system_user_id', 'api_tokens', ['system_user_id'])

    # 3. Add created_by_user_id column to api_tokens
    # This tracks which human user created the token
    # Initially nullable to support existing data, but will be required for new tokens
    op.add_column(
        'api_tokens',
        sa.Column('created_by_user_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_api_tokens_created_by_user_id',
        'api_tokens',
        'users',
        ['created_by_user_id'],
        ['id']
    )
    op.create_index('ix_api_tokens_created_by_user_id', 'api_tokens', ['created_by_user_id'])


def downgrade() -> None:
    """
    Reverse the changes: remove user_type and restore api_tokens structure.
    """
    # 1. Remove created_by_user_id from api_tokens
    op.drop_index('ix_api_tokens_created_by_user_id', table_name='api_tokens')
    op.drop_constraint('fk_api_tokens_created_by_user_id', 'api_tokens', type_='foreignkey')
    op.drop_column('api_tokens', 'created_by_user_id')

    # 2. Rename system_user_id back to user_id
    op.drop_index('ix_api_tokens_system_user_id', table_name='api_tokens')
    op.drop_constraint('fk_api_tokens_system_user_id', 'api_tokens', type_='foreignkey')

    op.alter_column('api_tokens', 'system_user_id', new_column_name='user_id')

    op.create_foreign_key(
        'fk_api_tokens_user_id',
        'api_tokens',
        'users',
        ['user_id'],
        ['id']
    )
    op.create_index('ix_api_tokens_user_id', 'api_tokens', ['user_id'])

    # 3. Remove user_type from users
    op.drop_index('ix_users_user_type', table_name='users')
    op.drop_column('users', 'user_type')

    # 4. Drop the enum type
    user_type_enum = sa.Enum('HUMAN', 'SYSTEM', name='user_type')
    user_type_enum.drop(op.get_bind(), checkfirst=True)
