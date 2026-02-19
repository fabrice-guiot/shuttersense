"""Add polymorphic target columns to jobs and analysis_results.

Revision ID: 072_polymorphic_target
Revises: 071_forces_skip_cancelled
Create Date: 2026-02-19

Issue #110: Polymorphic target entity for Job and AnalysisResult.
Adds target_entity_type, target_entity_id, target_entity_guid,
target_entity_name, and context_json columns to both tables.
Backfills existing rows from legacy FK columns.
"""

import json
import logging
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '072_polymorphic_target'
down_revision = '071_forces_skip_cancelled'
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.migration")


def upgrade():
    # Step 1: Add columns to both tables
    context_col_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    for table in ("analysis_results", "jobs"):
        op.add_column(table, sa.Column("target_entity_type", sa.String(30), nullable=True))
        op.add_column(table, sa.Column("target_entity_id", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("target_entity_guid", sa.String(50), nullable=True))
        op.add_column(table, sa.Column("target_entity_name", sa.String(255), nullable=True))
        op.add_column(table, sa.Column("context_json", context_col_type, nullable=True))

    # Step 2: Create indexes (dialect-aware)
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_results_target "
                "ON analysis_results (target_entity_type, target_entity_id)"
            )
            op.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_results_target_tool "
                "ON analysis_results (target_entity_type, target_entity_id, tool, created_at DESC)"
            )
            op.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_target "
                "ON jobs (target_entity_type, target_entity_id)"
            )
    else:
        op.create_index("idx_results_target", "analysis_results",
                        ["target_entity_type", "target_entity_id"])
        op.create_index("idx_results_target_tool", "analysis_results",
                        ["target_entity_type", "target_entity_id", "tool", "created_at"])
        op.create_index("idx_jobs_target", "jobs",
                        ["target_entity_type", "target_entity_id"])

    # Step 3: Backfill existing rows from legacy FK columns
    import uuid as uuid_mod
    import base32_crockford

    bind = op.get_bind()

    def encode_uuid(uuid_value, prefix):
        """Inline GUID encoding (avoids importing GuidService which triggers service __init__.py)."""
        if uuid_value is None:
            return None
        if isinstance(uuid_value, bytes):
            uuid_int = int.from_bytes(uuid_value, "big")
        elif isinstance(uuid_value, uuid_mod.UUID):
            uuid_int = int.from_bytes(uuid_value.bytes, "big")
        else:
            uuid_int = int.from_bytes(uuid_mod.UUID(str(uuid_value)).bytes, "big")
        encoded = base32_crockford.encode(uuid_int)
        return f"{prefix}_{encoded.zfill(26).lower()}"

    def to_uuid(val):
        """Convert a DB UUID value to uuid.UUID."""
        if val is None:
            return None
        if isinstance(val, uuid_mod.UUID):
            return val
        if isinstance(val, bytes):
            return uuid_mod.UUID(bytes=val)
        if isinstance(val, str):
            return uuid_mod.UUID(val)
        return val

    # --- Backfill analysis_results ---

    # 1. Collection-targeted results
    rows = bind.execute(sa.text("""
        SELECT ar.id, ar.collection_id, ar.pipeline_id, ar.pipeline_version,
               c.uuid AS col_uuid, c.name AS col_name, c.connector_id,
               p.uuid AS pip_uuid, p.name AS pip_name,
               cn.id AS cn_id, cn.uuid AS cn_uuid, cn.name AS cn_name
        FROM analysis_results ar
        JOIN collections c ON ar.collection_id = c.id
        LEFT JOIN pipelines p ON ar.pipeline_id = p.id
        LEFT JOIN connectors cn ON c.connector_id = cn.id
        WHERE ar.collection_id IS NOT NULL
          AND ar.target_entity_type IS NULL
    """)).fetchall()

    for row in rows:
        context = {}
        if row.pipeline_id:
            pip = {"guid": encode_uuid(to_uuid(row.pip_uuid), "pip"),
                   "name": row.pip_name, "version": row.pipeline_version}
            context["pipeline"] = {k: v for k, v in pip.items() if v is not None}
        if row.cn_id:
            con = {"guid": encode_uuid(to_uuid(row.cn_uuid), "con"),
                   "name": row.cn_name}
            context["connector"] = {k: v for k, v in con.items() if v is not None}

        bind.execute(sa.text("""
            UPDATE analysis_results
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = :ctx
            WHERE id = :id
        """), {
            "tet": "collection",
            "tei": row.collection_id,
            "teg": encode_uuid(to_uuid(row.col_uuid), "col"),
            "ten": row.col_name,
            "ctx": json.dumps(context) if context else None,
            "id": row.id,
        })

    # 2. Connector-targeted results (inventory tools)
    rows = bind.execute(sa.text("""
        SELECT ar.id, ar.connector_id, cn.uuid AS cn_uuid, cn.name AS cn_name
        FROM analysis_results ar
        JOIN connectors cn ON ar.connector_id = cn.id
        WHERE ar.collection_id IS NULL AND ar.connector_id IS NOT NULL
          AND ar.target_entity_type IS NULL
    """)).fetchall()

    for row in rows:
        bind.execute(sa.text("""
            UPDATE analysis_results
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = NULL
            WHERE id = :id
        """), {
            "tet": "connector",
            "tei": row.connector_id,
            "teg": encode_uuid(to_uuid(row.cn_uuid), "con"),
            "ten": row.cn_name,
            "id": row.id,
        })

    # 3. Pipeline-targeted results (display_graph)
    rows = bind.execute(sa.text("""
        SELECT ar.id, ar.pipeline_id, p.uuid AS pip_uuid, p.name AS pip_name
        FROM analysis_results ar
        JOIN pipelines p ON ar.pipeline_id = p.id
        WHERE ar.collection_id IS NULL AND ar.connector_id IS NULL
          AND ar.pipeline_id IS NOT NULL
          AND ar.target_entity_type IS NULL
    """)).fetchall()

    for row in rows:
        bind.execute(sa.text("""
            UPDATE analysis_results
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = NULL
            WHERE id = :id
        """), {
            "tet": "pipeline",
            "tei": row.pipeline_id,
            "teg": encode_uuid(to_uuid(row.pip_uuid), "pip"),
            "ten": row.pip_name,
            "id": row.id,
        })

    # --- Backfill jobs ---

    # 1. Collection-targeted jobs
    rows = bind.execute(sa.text("""
        SELECT j.id, j.collection_id, j.pipeline_id, j.pipeline_version,
               c.uuid AS col_uuid, c.name AS col_name, c.connector_id,
               p.uuid AS pip_uuid, p.name AS pip_name,
               cn.id AS cn_id, cn.uuid AS cn_uuid, cn.name AS cn_name
        FROM jobs j
        JOIN collections c ON j.collection_id = c.id
        LEFT JOIN pipelines p ON j.pipeline_id = p.id
        LEFT JOIN connectors cn ON c.connector_id = cn.id
        WHERE j.collection_id IS NOT NULL
          AND j.target_entity_type IS NULL
    """)).fetchall()

    for row in rows:
        context = {}
        if row.pipeline_id:
            pip = {"guid": encode_uuid(to_uuid(row.pip_uuid), "pip"),
                   "name": row.pip_name, "version": row.pipeline_version}
            context["pipeline"] = {k: v for k, v in pip.items() if v is not None}
        if row.cn_id:
            con = {"guid": encode_uuid(to_uuid(row.cn_uuid), "con"),
                   "name": row.cn_name}
            context["connector"] = {k: v for k, v in con.items() if v is not None}

        bind.execute(sa.text("""
            UPDATE jobs
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = :ctx
            WHERE id = :id
        """), {
            "tet": "collection",
            "tei": row.collection_id,
            "teg": encode_uuid(to_uuid(row.col_uuid), "col"),
            "ten": row.col_name,
            "ctx": json.dumps(context) if context else None,
            "id": row.id,
        })

    # 2. Pipeline-targeted jobs (display_graph)
    rows = bind.execute(sa.text("""
        SELECT j.id, j.pipeline_id, p.uuid AS pip_uuid, p.name AS pip_name
        FROM jobs j
        JOIN pipelines p ON j.pipeline_id = p.id
        WHERE j.collection_id IS NULL
          AND j.pipeline_id IS NOT NULL
          AND j.tool NOT IN ('inventory_validate', 'inventory_import')
          AND j.target_entity_type IS NULL
    """)).fetchall()

    for row in rows:
        bind.execute(sa.text("""
            UPDATE jobs
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = NULL
            WHERE id = :id
        """), {
            "tet": "pipeline",
            "tei": row.pipeline_id,
            "teg": encode_uuid(to_uuid(row.pip_uuid), "pip"),
            "ten": row.pip_name,
            "id": row.id,
        })

    # 3. Connector-targeted jobs (inventory tools) - from progress_json
    rows = bind.execute(sa.text("""
        SELECT j.id, j.progress_json
        FROM jobs j
        WHERE j.tool IN ('inventory_validate', 'inventory_import')
          AND j.target_entity_type IS NULL
    """)).fetchall()

    skipped_jobs = []
    for row in rows:
        raw = row.progress_json
        progress = raw if isinstance(raw, dict) else (json.loads(raw) if raw else {})
        connector_id = progress.get("connector_id")
        if not connector_id:
            skipped_jobs.append(row.id)
            continue

        cn = bind.execute(sa.text(
            "SELECT id, uuid, name FROM connectors WHERE id = :cid"
        ), {"cid": connector_id}).fetchone()

        if not cn:
            skipped_jobs.append(row.id)
            continue

        bind.execute(sa.text("""
            UPDATE jobs
            SET target_entity_type = :tet, target_entity_id = :tei,
                target_entity_guid = :teg, target_entity_name = :ten,
                context_json = NULL
            WHERE id = :id
        """), {
            "tet": "connector",
            "tei": cn.id,
            "teg": encode_uuid(to_uuid(cn.uuid), "con"),
            "ten": cn.name,
            "id": row.id,
        })

    if skipped_jobs:
        logger.warning(
            "Backfill skipped %d inventory jobs (missing connector_id or deleted connector): %s",
            len(skipped_jobs), skipped_jobs
        )


def downgrade():
    dialect = op.get_bind().dialect.name

    if dialect == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_results_target")
            op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_results_target_tool")
            op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_jobs_target")
    else:
        op.drop_index("idx_results_target", table_name="analysis_results")
        op.drop_index("idx_results_target_tool", table_name="analysis_results")
        op.drop_index("idx_jobs_target", table_name="jobs")

    for table in ("analysis_results", "jobs"):
        for col in ("context_json", "target_entity_name", "target_entity_guid",
                     "target_entity_id", "target_entity_type"):
            op.drop_column(table, col)
