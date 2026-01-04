"""Create configurations table

Revision ID: 005_configurations
Revises: 004_analysis_results
Create Date: 2026-01-04

Creates:
- configurations table for persistent application settings
- configsource enum for tracking configuration origin
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '005_configurations'
down_revision = '004_analysis_results'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create configurations table.

    Stores application configuration (extensions, cameras, processing methods)
    as category/key/value records with JSONB values for type flexibility.
    """

    # Create configsource enum
    configsource_enum = postgresql.ENUM(
        'database', 'yaml_import',
        name='configsource',
        create_type=False
    )
    configsource_enum.create(op.get_bind(), checkfirst=True)

    # Create configurations table
    op.create_table(
        'configurations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', configsource_enum, nullable=False, server_default='database'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes on configurations
    op.create_index('ix_configurations_category', 'configurations', ['category'], unique=False)
    op.create_index(
        'ix_configurations_category_key',
        'configurations',
        ['category', 'key'],
        unique=True
    )
    op.create_index('ix_configurations_source', 'configurations', ['source'], unique=False)


def downgrade() -> None:
    """
    Drop configurations table and configsource enum.

    Note: This will drop all configuration data.
    """
    # Drop indexes on configurations
    op.drop_index('ix_configurations_source', table_name='configurations')
    op.drop_index('ix_configurations_category_key', table_name='configurations')
    op.drop_index('ix_configurations_category', table_name='configurations')

    # Drop configurations table
    op.drop_table('configurations')

    # Drop configsource enum
    postgresql.ENUM(name='configsource').drop(op.get_bind(), checkfirst=True)
