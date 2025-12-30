"""Initial collections schema

Revision ID: 001_initial_collections
Revises:
Create Date: 2025-12-30

Creates connectors and collections tables with:
- Connectors table for remote storage credentials
- Collections table for photo collections (local and remote)
- Enums for connector type, collection type, and collection state
- Foreign key relationship (collections.connector_id -> connectors.id)
- Indexes for query performance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001_initial_collections'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create connectors and collections tables.

    Tables:
    - connectors: Remote storage connector configurations
    - collections: Photo collections (local and remote)

    Enums:
    - connector_type: s3, gcs, smb
    - collection_type: local, s3, gcs, smb
    - collection_state: live, closed, archived
    """

    # Create connector_type enum
    connector_type_enum = postgresql.ENUM(
        's3', 'gcs', 'smb',
        name='connectortype',
        create_type=False
    )
    connector_type_enum.create(op.get_bind(), checkfirst=True)

    # Create collection_type enum
    collection_type_enum = postgresql.ENUM(
        'local', 's3', 'gcs', 'smb',
        name='collectiontype',
        create_type=False
    )
    collection_type_enum.create(op.get_bind(), checkfirst=True)

    # Create collection_state enum
    collection_state_enum = postgresql.ENUM(
        'live', 'closed', 'archived',
        name='collectionstate',
        create_type=False
    )
    collection_state_enum.create(op.get_bind(), checkfirst=True)

    # Create connectors table
    op.create_table(
        'connectors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', connector_type_enum, nullable=False),
        sa.Column('credentials', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_validated', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes on connectors
    op.create_index('ix_connectors_name', 'connectors', ['name'], unique=True)
    op.create_index('ix_connectors_type', 'connectors', ['type'], unique=False)
    op.create_index('ix_connectors_is_active', 'connectors', ['is_active'], unique=False)

    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('connector_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', collection_type_enum, nullable=False),
        sa.Column('location', sa.String(length=1024), nullable=False),
        sa.Column('state', collection_state_enum, nullable=False, server_default='live'),
        sa.Column('cache_ttl', sa.Integer(), nullable=True),
        sa.Column('is_accessible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('name')
    )

    # Create indexes on collections
    op.create_index('ix_collections_name', 'collections', ['name'], unique=True)
    op.create_index('ix_collections_connector_id', 'collections', ['connector_id'], unique=False)
    op.create_index('ix_collections_type', 'collections', ['type'], unique=False)
    op.create_index('ix_collections_state', 'collections', ['state'], unique=False)
    op.create_index('ix_collections_is_accessible', 'collections', ['is_accessible'], unique=False)


def downgrade() -> None:
    """
    Drop connectors and collections tables.

    Note: This will drop all connectors and collections data.
    Use with caution in production.
    """
    # Drop indexes on collections
    op.drop_index('ix_collections_is_accessible', table_name='collections')
    op.drop_index('ix_collections_state', table_name='collections')
    op.drop_index('ix_collections_type', table_name='collections')
    op.drop_index('ix_collections_connector_id', table_name='collections')
    op.drop_index('ix_collections_name', table_name='collections')

    # Drop collections table
    op.drop_table('collections')

    # Drop indexes on connectors
    op.drop_index('ix_connectors_is_active', table_name='connectors')
    op.drop_index('ix_connectors_type', table_name='connectors')
    op.drop_index('ix_connectors_name', table_name='connectors')

    # Drop connectors table
    op.drop_table('connectors')

    # Drop enums
    postgresql.ENUM(name='collectionstate').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='collectiontype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='connectortype').drop(op.get_bind(), checkfirst=True)
