"""Split volatile agent fields into agent_runtime table.

Revision ID: 075_agent_runtime_table
Revises: 074_release_1_20_darwin_arm64
Create Date: 2026-02-22

Separates frequently-updated heartbeat/status fields from the agents table
into a new agent_runtime table (1:1 relationship). This allows SQLAlchemy's
onupdate on agents.updated_at to fire only for meaningful identity/config
changes, not routine heartbeats.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '075_agent_runtime_table'
down_revision = '074_release_1_20_darwin_arm64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_runtime table, migrate data, drop volatile columns from agents."""
    bind = op.get_bind()
    dialect = bind.dialect.name
    is_sqlite = dialect == "sqlite"

    # JSON column type per dialect
    json_type = sa.Text() if is_sqlite else JSONB()

    # Status enum — ensure native PG type exists, then reuse it
    if not is_sqlite:
        bind.execute(sa.text("""
            DO $$ BEGIN
                CREATE TYPE agent_status AS ENUM ('online', 'offline', 'error', 'revoked');
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """))

    status_enum = sa.Enum(
        "online", "offline", "error", "revoked",
        name="agent_status",
        create_constraint=False,
        create_type=False,  # handled above for PG; irrelevant for SQLite
    )
    # PostgreSQL needs explicit cast for enum default; SQLite accepts plain string
    status_default = "offline" if is_sqlite else sa.text("'offline'::agent_status")

    # ── Step 1: Create agent_runtime table ──
    op.create_table(
        "agent_runtime",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "agent_id",
            sa.Integer,
            sa.ForeignKey("agents.id", name="fk_agent_runtime_agent_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default=status_default,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("last_heartbeat", sa.DateTime, nullable=True),
        sa.Column("capabilities_json", json_type, nullable=False, server_default="[]"),
        sa.Column("authorized_roots_json", json_type, nullable=False, server_default="[]"),
        sa.Column("pending_commands_json", json_type, nullable=False, server_default="[]"),
        sa.Column("metrics_json", json_type, nullable=True),
    )

    # Indexes on the new table
    op.create_index("ix_agent_runtime_agent_id", "agent_runtime", ["agent_id"], unique=True)
    op.create_index("ix_agent_runtime_status", "agent_runtime", ["status"])

    # ── Step 2: Migrate data from agents to agent_runtime ──
    if is_sqlite:
        bind.execute(sa.text("""
            INSERT INTO agent_runtime (agent_id, status, error_message, last_heartbeat,
                                       capabilities_json, authorized_roots_json,
                                       pending_commands_json, metrics_json)
            SELECT id, status, error_message, last_heartbeat,
                   capabilities_json, authorized_roots_json,
                   pending_commands_json, metrics_json
            FROM agents
        """))
    else:
        # PostgreSQL: agents.status is VARCHAR(20) but SQLAlchemy's Enum() stores
        # enum .name (uppercase) by default. Cast via lower() to match the native
        # agent_status enum which has lowercase values.
        bind.execute(sa.text("""
            INSERT INTO agent_runtime (agent_id, status, error_message, last_heartbeat,
                                       capabilities_json, authorized_roots_json,
                                       pending_commands_json, metrics_json)
            SELECT id, lower(status)::agent_status, error_message, last_heartbeat,
                   capabilities_json, authorized_roots_json,
                   pending_commands_json, metrics_json
            FROM agents
        """))

    # ── Step 3: Drop volatile columns and old index from agents ──
    if is_sqlite:
        # SQLite requires batch_alter_table for column drops
        with op.batch_alter_table("agents") as batch_op:
            # Drop the composite index first
            batch_op.drop_index("ix_agents_team_status")
            # Drop the status column index
            try:
                batch_op.drop_index("ix_agents_status")
            except Exception:
                pass  # May not exist as a standalone index
            # Drop volatile columns
            batch_op.drop_column("status")
            batch_op.drop_column("error_message")
            batch_op.drop_column("last_heartbeat")
            batch_op.drop_column("capabilities_json")
            batch_op.drop_column("authorized_roots_json")
            batch_op.drop_column("pending_commands_json")
            batch_op.drop_column("metrics_json")
    else:
        # PostgreSQL: drop indexes if they exist, then columns
        bind.execute(sa.text("DROP INDEX IF EXISTS ix_agents_team_status"))
        bind.execute(sa.text("DROP INDEX IF EXISTS ix_agents_status"))
        op.drop_column("agents", "status")
        op.drop_column("agents", "error_message")
        op.drop_column("agents", "last_heartbeat")
        op.drop_column("agents", "capabilities_json")
        op.drop_column("agents", "authorized_roots_json")
        op.drop_column("agents", "pending_commands_json")
        op.drop_column("agents", "metrics_json")


def downgrade() -> None:
    """Move data back from agent_runtime to agents, drop agent_runtime table."""
    bind = op.get_bind()
    dialect = bind.dialect.name
    is_sqlite = dialect == "sqlite"

    json_type = sa.Text() if is_sqlite else JSONB()

    # Status enum — reuse existing PG enum type
    status_enum = sa.Enum(
        "online", "offline", "error", "revoked",
        name="agent_status",
        create_constraint=False,
        create_type=False,
    )
    status_default = "offline" if is_sqlite else sa.text("'offline'::agent_status")

    # ── Step 1: Re-add volatile columns to agents ──
    if is_sqlite:
        with op.batch_alter_table("agents") as batch_op:
            batch_op.add_column(sa.Column(
                "status",
                status_enum,
                nullable=False,
                server_default=status_default,
            ))
            batch_op.add_column(sa.Column("error_message", sa.Text, nullable=True))
            batch_op.add_column(sa.Column("last_heartbeat", sa.DateTime, nullable=True))
            batch_op.add_column(sa.Column("capabilities_json", json_type, nullable=False, server_default="[]"))
            batch_op.add_column(sa.Column("authorized_roots_json", json_type, nullable=False, server_default="[]"))
            batch_op.add_column(sa.Column("pending_commands_json", json_type, nullable=False, server_default="[]"))
            batch_op.add_column(sa.Column("metrics_json", json_type, nullable=True))
    else:
        op.add_column("agents", sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default=status_default,
        ))
        op.add_column("agents", sa.Column("error_message", sa.Text, nullable=True))
        op.add_column("agents", sa.Column("last_heartbeat", sa.DateTime, nullable=True))
        op.add_column("agents", sa.Column("capabilities_json", json_type, nullable=False, server_default="[]"))
        op.add_column("agents", sa.Column("authorized_roots_json", json_type, nullable=False, server_default="[]"))
        op.add_column("agents", sa.Column("pending_commands_json", json_type, nullable=False, server_default="[]"))
        op.add_column("agents", sa.Column("metrics_json", json_type, nullable=True))

    # ── Step 2: Copy data back ──
    if is_sqlite:
        # SQLite doesn't support UPDATE...FROM syntax
        bind.execute(sa.text("""
            UPDATE agents SET
                status = (SELECT rt.status FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                error_message = (SELECT rt.error_message FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                last_heartbeat = (SELECT rt.last_heartbeat FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                capabilities_json = (SELECT rt.capabilities_json FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                authorized_roots_json = (SELECT rt.authorized_roots_json FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                pending_commands_json = (SELECT rt.pending_commands_json FROM agent_runtime rt WHERE rt.agent_id = agents.id),
                metrics_json = (SELECT rt.metrics_json FROM agent_runtime rt WHERE rt.agent_id = agents.id)
            WHERE agents.id IN (SELECT agent_id FROM agent_runtime)
        """))
    else:
        bind.execute(sa.text("""
            UPDATE agents SET
                status = rt.status,
                error_message = rt.error_message,
                last_heartbeat = rt.last_heartbeat,
                capabilities_json = rt.capabilities_json,
                authorized_roots_json = rt.authorized_roots_json,
                pending_commands_json = rt.pending_commands_json,
                metrics_json = rt.metrics_json
            FROM agent_runtime rt
            WHERE agents.id = rt.agent_id
        """))

    # ── Step 3: Recreate indexes ──
    op.create_index("ix_agents_team_status", "agents", ["team_id", "status"])
    op.create_index("ix_agents_status", "agents", ["status"])

    # ── Step 4: Drop agent_runtime table ──
    op.drop_index("ix_agent_runtime_status", table_name="agent_runtime")
    op.drop_index("ix_agent_runtime_agent_id", table_name="agent_runtime")
    op.drop_table("agent_runtime")
