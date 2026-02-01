"""Add audit user attribution columns.

Revision ID: 058_add_audit_user_columns
Revises: 057_push_notifications
Create Date: 2026-01-31

Issue #120: Audit Trail Visibility Enhancement
- Add created_by_user_id and updated_by_user_id to 14 Group A tables
- Add updated_by_user_id to 3 Group B tables (already have created_by_user_id)
- Add indexes for all new columns
- PostgreSQL: CREATE INDEX CONCURRENTLY for large tables (outside transaction)
- Add immutability trigger for created_by_user_id (PostgreSQL only)
"""
from alembic import op
import sqlalchemy as sa

revision = '058_add_audit_user_columns'
down_revision = '057_push_notifications'
branch_labels = None
depends_on = None

# Group A: Get both created_by_user_id and updated_by_user_id
GROUP_A_TABLES = [
    "collections",
    "connectors",
    "pipelines",
    "jobs",
    "analysis_results",
    "events",
    "event_series",
    "categories",
    "locations",
    "organizers",
    "performers",
    "configurations",
    "push_subscriptions",
    "notifications",
]

# Group B: Already have created_by_user_id, only need updated_by_user_id
GROUP_B_TABLES = [
    "agents",
    "api_tokens",
    "agent_registration_tokens",
]

ALL_TABLES = GROUP_A_TABLES + GROUP_B_TABLES

# Large tables that benefit from CONCURRENTLY index creation (PostgreSQL)
LARGE_TABLES = {"collections", "jobs", "analysis_results", "events", "notifications"}


def upgrade() -> None:
    """Add audit user attribution columns and indexes to all entity tables.

    Adds created_by_user_id and updated_by_user_id foreign key columns to
    14 Group A tables and updated_by_user_id to 3 Group B tables (which
    already have created_by_user_id). Creates indexes on all new columns
    and an immutability trigger for created_by_user_id on PostgreSQL.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Modifies DB schema via Alembic op: adds columns, creates indexes
        (CONCURRENTLY on large PostgreSQL tables), and installs an immutability
        trigger function on PostgreSQL.
    """
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- Phase 1: Add columns (transactional) ---

    for table in GROUP_A_TABLES:
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

    for table in GROUP_B_TABLES:
        op.add_column(
            table,
            sa.Column(
                "updated_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    # --- Phase 2: Create indexes on small tables (transactional) ---

    small_tables = [t for t in ALL_TABLES if t not in LARGE_TABLES]
    for table in small_tables:
        op.create_index(f"ix_{table}_updated_by_user_id", table, ["updated_by_user_id"])

    small_group_a = [t for t in GROUP_A_TABLES if t not in LARGE_TABLES]
    for table in small_group_a:
        op.create_index(f"ix_{table}_created_by_user_id", table, ["created_by_user_id"])

    # --- Phase 3: Immutability trigger (PostgreSQL only, transactional) ---

    if is_pg:
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_created_by_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
              IF OLD.created_by_user_id IS NOT NULL
                 AND NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id THEN
                RAISE EXCEPTION 'created_by_user_id is immutable once set (table: %, old: %, new: %)',
                  TG_TABLE_NAME, OLD.created_by_user_id, NEW.created_by_user_id;
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        for table in GROUP_A_TABLES:
            trigger_name = f"trg_{table}_immutable_created_by"
            op.execute(sa.text(f"""
                CREATE TRIGGER {trigger_name}
                  BEFORE UPDATE ON {table}
                  FOR EACH ROW
                  EXECUTE FUNCTION prevent_created_by_mutation();
            """))

    # --- Phase 4: Indexes on large tables ---
    # Use regular CREATE INDEX (not CONCURRENTLY) to stay within Alembic's
    # transaction. CONCURRENTLY requires running outside a transaction block
    # which is incompatible with Alembic's default transactional DDL.

    for table in sorted(LARGE_TABLES):
        op.create_index(
            f"ix_{table}_updated_by_user_id", table, ["updated_by_user_id"]
        )
        if table in GROUP_A_TABLES:
            op.create_index(
                f"ix_{table}_created_by_user_id", table, ["created_by_user_id"]
            )


def downgrade() -> None:
    """Remove audit user attribution columns, indexes, and triggers.

    Reverses upgrade() by dropping the immutability trigger and function
    (PostgreSQL only), dropping all indexes on audit columns, and removing
    the created_by_user_id and updated_by_user_id columns from all tables.

    Args:
        None.

    Returns:
        None.

    Side Effects:
        Modifies DB schema via Alembic op: drops triggers, indexes
        (CONCURRENTLY on large PostgreSQL tables), and columns.
    """
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- Phase 1: Drop triggers (PostgreSQL only) ---

    if is_pg:
        for table in GROUP_A_TABLES:
            trigger_name = f"trg_{table}_immutable_created_by"
            op.execute(sa.text(
                f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}"
            ))
        op.execute(sa.text(
            "DROP FUNCTION IF EXISTS prevent_created_by_mutation()"
        ))

    # --- Phase 2: Drop indexes ---

    for table in ALL_TABLES:
        op.drop_index(f"ix_{table}_updated_by_user_id", table_name=table)

    for table in GROUP_A_TABLES:
        op.drop_index(f"ix_{table}_created_by_user_id", table_name=table)

    # --- Phase 4: Drop columns ---

    for table in GROUP_B_TABLES:
        op.drop_column(table, "updated_by_user_id")

    for table in GROUP_A_TABLES:
        op.drop_column(table, "updated_by_user_id")
        op.drop_column(table, "created_by_user_id")
