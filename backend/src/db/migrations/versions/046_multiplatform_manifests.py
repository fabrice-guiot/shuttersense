"""Convert release manifests from single platform to multi-platform support.

Revision ID: 046_multiplatform_manifests
Revises: 045_create_release_manifests
Create Date: 2026-01-21

Changes:
- Add platforms_json column (JSONB for PostgreSQL, TEXT for SQLite)
- Migrate existing platform values to platforms array
- Drop old unique constraint (version, platform)
- Create new unique constraint (version, checksum)
- Drop platform column

This enables universal binaries (macOS) that run on multiple architectures
to have a single manifest entry with multiple platforms.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '046_multiplatform_manifests'
down_revision = '045_create_release_manifests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add platforms_json column and migrate from platform column."""
    # Get the current database dialect
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Step 1: Add platforms_json column (nullable initially)
    if dialect == 'postgresql':
        op.add_column(
            'release_manifests',
            sa.Column('platforms_json', postgresql.JSONB(), nullable=True)
        )
    else:
        # SQLite uses TEXT
        op.add_column(
            'release_manifests',
            sa.Column('platforms_json', sa.Text(), nullable=True)
        )

    # Step 2: Migrate data - convert platform to [platform]
    if dialect == 'postgresql':
        op.execute("""
            UPDATE release_manifests
            SET platforms_json = jsonb_build_array(platform)
            WHERE platform IS NOT NULL
        """)
        # Handle any NULL platforms
        op.execute("""
            UPDATE release_manifests
            SET platforms_json = '[]'::jsonb
            WHERE platforms_json IS NULL
        """)
    else:
        # SQLite: store as JSON string
        op.execute("""
            UPDATE release_manifests
            SET platforms_json = '["' || platform || '"]'
            WHERE platform IS NOT NULL
        """)
        op.execute("""
            UPDATE release_manifests
            SET platforms_json = '[]'
            WHERE platforms_json IS NULL
        """)

    # Step 3: Make platforms_json NOT NULL
    op.alter_column(
        'release_manifests',
        'platforms_json',
        nullable=False
    )

    # Step 4: Drop old unique constraint and index
    op.drop_index('uq_release_version_platform', table_name='release_manifests')
    op.drop_index('ix_release_manifests_platform', table_name='release_manifests')

    # Step 5: Create new unique constraint (version, checksum)
    op.create_index(
        'uq_release_version_checksum',
        'release_manifests',
        ['version', 'checksum'],
        unique=True
    )

    # Step 6: Drop the old platform column
    op.drop_column('release_manifests', 'platform')


def downgrade() -> None:
    """Revert to single platform column."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Step 1: Add platform column back
    op.add_column(
        'release_manifests',
        sa.Column('platform', sa.String(50), nullable=True)
    )

    # Step 2: Migrate data - extract first platform from array
    if dialect == 'postgresql':
        op.execute("""
            UPDATE release_manifests
            SET platform = platforms_json->>0
            WHERE platforms_json IS NOT NULL AND jsonb_array_length(platforms_json) > 0
        """)
    else:
        # SQLite: parse JSON and extract first element
        op.execute("""
            UPDATE release_manifests
            SET platform = json_extract(platforms_json, '$[0]')
            WHERE platforms_json IS NOT NULL AND platforms_json != '[]'
        """)

    # Step 3: Make platform NOT NULL (may fail if any have empty arrays)
    op.alter_column(
        'release_manifests',
        'platform',
        nullable=False
    )

    # Step 4: Drop new unique constraint
    op.drop_index('uq_release_version_checksum', table_name='release_manifests')

    # Step 5: Recreate old indexes and constraint
    op.create_index('ix_release_manifests_platform', 'release_manifests', ['platform'])
    op.create_index(
        'uq_release_version_platform',
        'release_manifests',
        ['version', 'platform'],
        unique=True
    )

    # Step 6: Drop platforms_json column
    op.drop_column('release_manifests', 'platforms_json')
