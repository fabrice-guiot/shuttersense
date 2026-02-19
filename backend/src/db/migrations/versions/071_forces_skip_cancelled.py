"""Add forces_skip to cancelled event status config.

Revision ID: 071_forces_skip_cancelled
Revises: 070_release_1_18_darwin_arm64
Create Date: 2026-02-19

Issue #238: Configurable event statuses trigger attendance behaviors.
Adds forces_skip=true to the 'cancelled' status for all existing teams.
Forward-only: does not retroactively update existing event attendance.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '071_forces_skip_cancelled'
down_revision = '070_release_1_18_darwin_arm64'
branch_labels = None
depends_on = None

# Reference to the configurations table
configurations = table(
    'configurations',
    column('id', sa.Integer),
    column('category', sa.String),
    column('key', sa.String),
    column('value_json', JSONB),
    column('team_id', sa.Integer),
)


def upgrade() -> None:
    """Add forces_skip=true to 'cancelled' event status for all teams."""
    conn = op.get_bind()

    # Find all 'cancelled' event status configurations
    rows = conn.execute(
        sa.select(configurations.c.id, configurations.c.value_json).where(
            sa.and_(
                configurations.c.category == 'event_statuses',
                configurations.c.key == 'cancelled',
            )
        )
    ).fetchall()

    for row in rows:
        value = dict(row.value_json) if row.value_json else {}
        value['forces_skip'] = True
        conn.execute(
            configurations.update()
            .where(configurations.c.id == row.id)
            .values(value_json=value)
        )


def downgrade() -> None:
    """Remove forces_skip from 'cancelled' event status for all teams."""
    conn = op.get_bind()

    rows = conn.execute(
        sa.select(configurations.c.id, configurations.c.value_json).where(
            sa.and_(
                configurations.c.category == 'event_statuses',
                configurations.c.key == 'cancelled',
            )
        )
    ).fetchall()

    for row in rows:
        value = dict(row.value_json) if row.value_json else {}
        value.pop('forces_skip', None)
        conn.execute(
            configurations.update()
            .where(configurations.c.id == row.id)
            .values(value_json=value)
        )
