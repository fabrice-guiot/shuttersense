"""Fix release_manifests uuid column type for PostgreSQL.

Revision ID: 047_fix_manifests_uuid
Revises: 046_multiplatform_manifests
Create Date: 2026-01-21

The uuid column was incorrectly created as bytea (LargeBinary) but needs to be
native UUID for PostgreSQL to match the SQLAlchemy UUIDType which uses
PostgreSQL's native UUID type.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '047_fix_manifests_uuid'
down_revision = '046_multiplatform_manifests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert uuid column from bytea to native UUID for PostgreSQL."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # Drop the existing index on uuid
        op.drop_index('ix_release_manifests_uuid', table_name='release_manifests')

        # Alter the column type from bytea to UUID
        # Convert bytea (16 bytes) to UUID format string then to UUID type
        # Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        op.execute("""
            ALTER TABLE release_manifests
            ALTER COLUMN uuid TYPE UUID USING (
                substring(encode(uuid, 'hex') from 1 for 8) || '-' ||
                substring(encode(uuid, 'hex') from 9 for 4) || '-' ||
                substring(encode(uuid, 'hex') from 13 for 4) || '-' ||
                substring(encode(uuid, 'hex') from 17 for 4) || '-' ||
                substring(encode(uuid, 'hex') from 21 for 12)
            )::uuid
        """)

        # Recreate the unique index
        op.create_index(
            'ix_release_manifests_uuid',
            'release_manifests',
            ['uuid'],
            unique=True
        )
    # SQLite uses LargeBinary(16) which is correct - no change needed


def downgrade() -> None:
    """Convert uuid column back to bytea for PostgreSQL."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # Drop the index
        op.drop_index('ix_release_manifests_uuid', table_name='release_manifests')

        # Convert UUID back to bytea (decode hex string to bytes)
        op.execute("""
            ALTER TABLE release_manifests
            ALTER COLUMN uuid TYPE bytea USING decode(replace(uuid::text, '-', ''), 'hex')
        """)

        # Recreate the index
        op.create_index(
            'ix_release_manifests_uuid',
            'release_manifests',
            ['uuid'],
            unique=True
        )
