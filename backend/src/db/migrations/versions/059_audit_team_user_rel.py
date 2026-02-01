"""Add audit columns to teams, users, release_manifests.

Revision ID: 059_audit_team_user_rel
Revises: 058_add_audit_user_columns
Create Date: 2026-02-01

Issue #120: Audit Trail Visibility Enhancement — extend audit to remaining entities.
- Add created_by_user_id and updated_by_user_id to teams, users, release_manifests
- Add indexes for all new columns
- Add immutability trigger for created_by_user_id (PostgreSQL only)

Note: users.created_by_user_id is a self-referencing FK (users → users).
"""
from alembic import op
import sqlalchemy as sa

revision = '059_audit_team_user_rel'
down_revision = '058_add_audit_user_columns'
branch_labels = None
depends_on = None

TABLES = ["teams", "users", "release_manifests"]


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- Phase 1: Add columns ---

    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "created_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "updated_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    # --- Phase 2: Create indexes ---

    for table in TABLES:
        op.create_index(f"ix_{table}_created_by_user_id", table, ["created_by_user_id"])
        op.create_index(f"ix_{table}_updated_by_user_id", table, ["updated_by_user_id"])

    # --- Phase 3: Immutability trigger (PostgreSQL only) ---
    # Reuse the prevent_created_by_mutation() function created in migration 058.

    if is_pg:
        for table in TABLES:
            trigger_name = f"trg_{table}_immutable_created_by"
            op.execute(sa.text(f"""
                CREATE TRIGGER {trigger_name}
                  BEFORE UPDATE ON {table}
                  FOR EACH ROW
                  EXECUTE FUNCTION prevent_created_by_mutation();
            """))


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- Phase 1: Drop triggers (PostgreSQL only) ---

    if is_pg:
        for table in TABLES:
            trigger_name = f"trg_{table}_immutable_created_by"
            op.execute(sa.text(
                f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}"
            ))

    # --- Phase 2: Drop indexes ---

    for table in TABLES:
        op.drop_index(f"ix_{table}_updated_by_user_id", table_name=table)
        op.drop_index(f"ix_{table}_created_by_user_id", table_name=table)

    # --- Phase 3: Drop columns ---

    for table in TABLES:
        op.drop_column(table, "updated_by_user_id")
        op.drop_column(table, "created_by_user_id")
