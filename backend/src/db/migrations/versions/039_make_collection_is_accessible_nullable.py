"""Make collection is_accessible nullable for pending state.

Revision ID: 039
Revises: 038
Create Date: 2026-01-19

Issue #90 - Distributed Agent Architecture

When a collection_test job is created for a LOCAL collection,
is_accessible should be set to NULL to indicate the test is pending.
This allows the UI to show a "Pending" state while waiting for
the agent to complete the accessibility test.

- NULL = pending/unknown (test in progress)
- True = accessible
- False = not accessible
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "039_is_accessible_nullable"
down_revision = "038_agent_auth_roots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make is_accessible nullable."""
    # Alter column to be nullable
    op.alter_column(
        "collections",
        "is_accessible",
        existing_type=sa.Boolean(),
        nullable=True,
    )


def downgrade() -> None:
    """Revert is_accessible to non-nullable."""
    # First, set any NULL values to True (default)
    op.execute("UPDATE collections SET is_accessible = TRUE WHERE is_accessible IS NULL")

    # Then alter column back to non-nullable
    op.alter_column(
        "collections",
        "is_accessible",
        existing_type=sa.Boolean(),
        nullable=False,
    )
