"""Add NO_CHANGE value to resultstatus enum.

Revision ID: 051_add_no_change_result_status
Revises: 050_seed_retention_defaults
Create Date: 2026-01-23

Issue #92: Storage Optimization for Analysis Results
- Add NO_CHANGE enum value to resultstatus PostgreSQL enum type
- This value is used for results that reference a previous result's report
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '051_add_no_change_result_status'
down_revision = '050_seed_retention_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add NO_CHANGE to resultstatus enum."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # PostgreSQL requires ALTER TYPE to add enum values
        # We cannot use parameters here, must use raw SQL
        op.execute("ALTER TYPE resultstatus ADD VALUE IF NOT EXISTS 'NO_CHANGE'")
    # SQLite stores enums as strings, so no migration needed


def downgrade() -> None:
    """Remove NO_CHANGE from resultstatus enum.

    Note: PostgreSQL does not support removing enum values easily.
    This would require recreating the type and all dependent columns.
    For safety, we just log a warning.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # Cannot easily remove enum values in PostgreSQL
        # Would need to: create new type, update columns, drop old type
        print("WARNING: Cannot remove NO_CHANGE from resultstatus enum. "
              "Manual intervention required if downgrade is necessary.")
