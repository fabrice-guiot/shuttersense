"""Add inventory import tables and columns.

Revision ID: 053_inventory_import_tables
Revises: 052_config_team_scoped_unique
Create Date: 2026-01-25

Issue #107: Cloud Storage Bucket Inventory Import
- Create inventory_folders table for discovered folders
- Add inventory configuration fields to connectors table
- Add FileInfo cache fields to collections table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '053_inventory_import_tables'
down_revision = '052_config_team_scoped'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add inventory import tables and columns."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # =========================================================================
    # Create inventory_folders table
    # =========================================================================
    if dialect == 'postgresql':
        op.create_table(
            'inventory_folders',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
            sa.Column('connector_id', sa.Integer(), sa.ForeignKey('connectors.id', ondelete='CASCADE'), nullable=False),
            sa.Column('path', sa.String(1024), nullable=False),
            sa.Column('object_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('deepest_modified', sa.DateTime(), nullable=True),
            sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('collection_guid', sa.String(30), nullable=True),
        )
    else:
        # SQLite: use LargeBinary for UUID
        op.create_table(
            'inventory_folders',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('uuid', sa.LargeBinary(16), nullable=False, unique=True, index=True),
            sa.Column('connector_id', sa.Integer(), sa.ForeignKey('connectors.id', ondelete='CASCADE'), nullable=False),
            sa.Column('path', sa.String(1024), nullable=False),
            sa.Column('object_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
            sa.Column('deepest_modified', sa.DateTime(), nullable=True),
            sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.text("datetime('now')")),
            sa.Column('collection_guid', sa.String(30), nullable=True),
        )

    # Create indexes for inventory_folders
    op.create_unique_constraint(
        'uq_inventory_folder_path',
        'inventory_folders',
        ['connector_id', 'path']
    )
    op.create_index(
        'ix_inventory_folder_connector',
        'inventory_folders',
        ['connector_id']
    )
    op.create_index(
        'ix_inventory_folder_collection',
        'inventory_folders',
        ['collection_guid']
    )

    # =========================================================================
    # Add inventory configuration columns to connectors table
    # =========================================================================
    if dialect == 'postgresql':
        op.add_column('connectors', sa.Column(
            'inventory_config',
            postgresql.JSONB(),
            nullable=True,
            comment='S3/GCS inventory source configuration'
        ))
    else:
        op.add_column('connectors', sa.Column(
            'inventory_config',
            sa.JSON(),
            nullable=True,
            comment='S3/GCS inventory source configuration'
        ))

    op.add_column('connectors', sa.Column(
        'inventory_validation_status',
        sa.String(20),
        nullable=True,
        comment='Validation status: pending/validating/validated/failed'
    ))
    op.add_column('connectors', sa.Column(
        'inventory_validation_error',
        sa.String(500),
        nullable=True,
        comment='Error message if validation failed'
    ))
    op.add_column('connectors', sa.Column(
        'inventory_last_import_at',
        sa.DateTime(),
        nullable=True,
        comment='Timestamp of last successful inventory import'
    ))
    op.add_column('connectors', sa.Column(
        'inventory_schedule',
        sa.String(20),
        server_default='manual',
        nullable=True,
        comment='Import schedule: manual/daily/weekly'
    ))

    # =========================================================================
    # Add FileInfo cache columns to collections table
    # =========================================================================
    if dialect == 'postgresql':
        op.add_column('collections', sa.Column(
            'file_info',
            postgresql.JSONB(),
            nullable=True,
            comment='Cached FileInfo array from inventory or API'
        ))
        op.add_column('collections', sa.Column(
            'file_info_delta',
            postgresql.JSONB(),
            nullable=True,
            comment='Delta summary: new/modified/deleted counts'
        ))
    else:
        op.add_column('collections', sa.Column(
            'file_info',
            sa.JSON(),
            nullable=True,
            comment='Cached FileInfo array from inventory or API'
        ))
        op.add_column('collections', sa.Column(
            'file_info_delta',
            sa.JSON(),
            nullable=True,
            comment='Delta summary: new/modified/deleted counts'
        ))

    op.add_column('collections', sa.Column(
        'file_info_updated_at',
        sa.DateTime(),
        nullable=True,
        comment='When FileInfo was last updated'
    ))
    op.add_column('collections', sa.Column(
        'file_info_source',
        sa.String(20),
        nullable=True,
        comment='FileInfo source: api or inventory'
    ))


def downgrade() -> None:
    """Remove inventory import tables and columns."""
    # Drop FileInfo columns from collections
    op.drop_column('collections', 'file_info_source')
    op.drop_column('collections', 'file_info_updated_at')
    op.drop_column('collections', 'file_info_delta')
    op.drop_column('collections', 'file_info')

    # Drop inventory columns from connectors
    op.drop_column('connectors', 'inventory_schedule')
    op.drop_column('connectors', 'inventory_last_import_at')
    op.drop_column('connectors', 'inventory_validation_error')
    op.drop_column('connectors', 'inventory_validation_status')
    op.drop_column('connectors', 'inventory_config')

    # Drop inventory_folders table
    op.drop_index('ix_inventory_folder_collection', table_name='inventory_folders')
    op.drop_index('ix_inventory_folder_connector', table_name='inventory_folders')
    op.drop_constraint('uq_inventory_folder_path', 'inventory_folders', type_='unique')
    op.drop_table('inventory_folders')
