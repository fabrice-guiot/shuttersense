# Implementation Plan: Polymorphic Target Entity for Job & AnalysisResult

**Branch**: `110-polymorphic-results` | **Date**: 2026-02-19 | **Issue**: [#110](https://github.com/fabrice-guiot/shuttersense/issues/110)
**Status**: Rev 2 — updated from reviewer feedback (CodeRabbit, Greptile)

## Summary

Refactor the `Job` and `AnalysisResult` data models to replace the growing set of nullable FK columns (`collection_id`, `pipeline_id`, `connector_id`) with a **polymorphic primary target** and a **JSONB context field** for secondary entity references. This enables long-term scalability as new analyzable entity types (Camera, Album, Workflow, Event) are added, and immediately improves the UI by surfacing entity names with navigation links.

**Technical approach**: Add a polymorphic primary target (`target_entity_type` + `target_entity_id` + cached guid/name) and a `context_json` JSONB column to both `Job` and `AnalysisResult`. The primary target identifies _what_ is being analyzed. The context captures _what tools/settings were used_ (pipeline, connector, etc.) as a point-in-time snapshot. A phased migration preserves all existing data and maintains backward compatibility through dual-write and deprecated-but-present API fields.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); React 18.3.1, shadcn/ui (frontend)
**Storage**: PostgreSQL 12+ (production), SQLite (tests) — additive columns on existing `analysis_results` and `jobs` tables
**Testing**: pytest (backend), frontend type-checking via `tsc --noEmit`
**Constraints**: DB-agnostic migration (SQLite tests); Alembic revision IDs <=32 chars; GuidMixin.guid is a @property (not filterable in SQLAlchemy); no agent binary changes

## Motivation

### Current Problem

Both `Job` and `AnalysisResult` have direct nullable FK columns for each entity type they can target:

```text
analysis_results:  collection_id (FK), pipeline_id (FK), connector_id (FK)
jobs:              collection_id (FK), pipeline_id (FK)
                   connector_id stored in progress_json (HACK)
```

Every new analyzable entity type requires: a new nullable FK column, a new Alembic migration, new indexes, null-check logic sprawl across services, schema changes on backend and frontend, and new JOIN paths for name resolution.

The `connector_id` on Job is especially problematic — it was never added as a proper FK and lives as a workaround inside `progress_json`.

### Why Now

- Production data is accumulating — the migration backfill will only get more complex over time
- The `domain-model.md` already describes Camera, Album, Workflow, and Event as future analysis targets
- Issue #217 just added the Camera entity — Camera-targeted analysis tools are imminent
- The current UI shows raw GUIDs where it should show entity names with links

## Design: Polymorphic Primary Target + JSONB Context

### Two-Part Model

Every Job/Result involves a **primary target** (the entity being analyzed) and optional **context** (related entities that provided configuration or access):

| Tool | Primary Target | Context |
|------|---------------|---------|
| `photostats` | Collection | pipeline (guid, name, version), connector (guid, name) if remote |
| `photo_pairing` | Collection | pipeline (guid, name, version), connector (guid, name) if remote |
| `pipeline_validation` (collection mode) | Collection | pipeline (guid, name, version) |
| `pipeline_validation` (display_graph) | Pipeline | — |
| `collection_test` | Collection | connector (guid, name) if remote |
| `inventory_validate` | Connector | — |
| `inventory_import` | Connector | — |
| _future: camera_health_ | _Camera_ | — |
| _future: album_completeness_ | _Album_ | _pipeline, workflow_ |

### New Columns (on both `analysis_results` and `jobs`)

```sql
-- Primary target: polymorphic, one per record
target_entity_type  VARCHAR(30)   -- "collection", "connector", "pipeline", "camera", ...
target_entity_id    INTEGER       -- internal ID of the target entity
target_entity_guid  VARCHAR(50)   -- cached GUID for API responses (avoids joins)
target_entity_name  VARCHAR(255)  -- cached display name (avoids joins)

-- Context: snapshot of secondary entity references
context_json        JSONB         -- structured context (see below), NULL when no context
```

### Context JSON Structure

When context exists, `context_json` contains only the keys that are relevant (no null-valued keys):

```json
{
  "pipeline": {
    "id": 5,
    "guid": "pip_01hgw2bbg0000000000000002",
    "name": "Standard RAW Workflow",
    "version": 3
  },
  "connector": {
    "id": 12,
    "guid": "con_01hgw2bbg0000000000000001",
    "name": "AWS Production S3"
  }
}
```

**Null handling convention**: When no context entities exist (e.g., inventory tools have no pipeline or connector context), `context_json` is `NULL` — not `{}` or `{"pipeline": null}`. When only some context exists (e.g., pipeline but no connector), only the present keys are included. This ensures consistency between backfilled records and newly-written records (Pydantic's `exclude_none=True` produces the same format).

Context is a **point-in-time snapshot**:
- Even if a pipeline is renamed or deleted, the context preserves what was used at execution time
- This is _better_ than the current FK-with-SET-NULL behavior, which loses pipeline references on delete
- No JOINs needed to resolve names in list views — guid and name are cached

### Target Entity Type Enum

Both Python and TypeScript define the **same** set of accepted entity types:

```python
# backend/src/models/__init__.py
class TargetEntityType(str, enum.Enum):
    COLLECTION = "collection"
    CONNECTOR = "connector"
    PIPELINE = "pipeline"
    CAMERA = "camera"
    # Future (no schema change needed):
    # ALBUM = "album"
    # EVENT = "event"
    # WORKFLOW = "workflow"
```

```typescript
// frontend/src/contracts/api/target-api.ts
export type TargetEntityType = 'collection' | 'connector' | 'pipeline' | 'camera'
```

> **Reviewer feedback addressed**: `CAMERA` is included in both Python and TypeScript enums to keep them aligned. Camera is already a model in the codebase (Issue #217). Future types (`ALBUM`, `EVENT`, `WORKFLOW`) remain commented out until their models exist.

### Why This Over Alternatives

| Approach | Verdict | Reasoning |
|----------|---------|-----------|
| **Junction tables** (`job_targets`) | Rejected | Over-engineered for single-cardinality primary target. Every Job/Result has exactly ONE primary target. |
| **Keep FKs + add discriminator** | Rejected | Doesn't solve column proliferation. Still need a new nullable FK per entity type. |
| **Multiple polymorphic columns** (target1, target2) | Rejected | Arbitrary cardinality limit. Doesn't capture the _role_ of each entity. |
| **Polymorphic target only (no context)** | Rejected | Loses pipeline version tracking and connector info for remote collections. |
| **Polymorphic target + JSONB context** | **Selected** | Two columns for primary target handle any future entity type. JSONB context captures all secondary references with their roles. Zero schema changes for new entity types. |

### Trade-offs

1. **No DB referential integrity on `target_entity_id`**: Mitigated by application-level validation on create (verify entity exists) and legacy FK columns during transition period.

2. **No DB referential integrity on context**: Acceptable. Context is a point-in-time snapshot — values are the correct historical record regardless of entity lifecycle.

3. **`pipeline_id` FK removed from AnalysisResult (Phase 4)**: The current FK was SET NULL on pipeline delete, which _loses_ the reference. Context JSON _preserves_ it permanently. This is an improvement.

4. **Cached `target_entity_name` can become stale**: If a collection is renamed, existing results still show the old name. This matches user expectation (the result was produced when the collection had that name). For critical use cases, the cached name can be refreshed via a background task (not in scope for this issue).

## Phased Migration Strategy

### Phase 1: Migration — Add Columns + Backfill Data

**Migration**: `072_polymorphic_target.py` (22 chars — under the 32-char limit)

#### Step 1: Add columns

Add 5 columns to both `analysis_results` and `jobs` (all nullable):

```python
# Dialect-aware JSONB column type (used for context_json)
context_col_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
```

- `target_entity_type`: `String(30)`, nullable
- `target_entity_id`: `Integer`, nullable
- `target_entity_guid`: `String(50)`, nullable
- `target_entity_name`: `String(255)`, nullable
- `context_json`: `context_col_type`, nullable

#### Step 2: Create indexes (dialect-aware)

On **PostgreSQL**: Use `CREATE INDEX CONCURRENTLY` via `op.execute()` to avoid write-locks on production tables. This requires the migration to run outside an Alembic transaction block (`autocommit` mode for this migration).

On **SQLite** (tests): Use standard `op.create_index()`.

```python
dialect = op.get_bind().dialect.name

if dialect == "postgresql":
    # Non-blocking index creation for production
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
    # SQLite — standard index creation
    op.create_index("idx_results_target", "analysis_results", ["target_entity_type", "target_entity_id"])
    op.create_index("idx_results_target_tool", "analysis_results", ["target_entity_type", "target_entity_id", "tool", "created_at"])
    op.create_index("idx_jobs_target", "jobs", ["target_entity_type", "target_entity_id"])
```

#### Step 3: Python-based backfill

> **Reviewer feedback addressed**: The backfill is **entirely Python-based** (not raw SQL). This solves three problems at once:
> 1. **GUID encoding**: Crockford Base32 is application logic in `GuidService` — cannot be done in SQL
> 2. **Dialect compatibility**: No `json_build_object()` vs `json_object()` branching needed
> 3. **context_json null handling**: Python can build dicts and skip null keys cleanly

**Backfill algorithm** (runs inside `upgrade()`):

```python
from backend.src.services.guid import GuidService

bind = op.get_bind()

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
        context["pipeline"] = {
            "id": row.pipeline_id,
            "guid": GuidService.uuid_to_guid("pip", row.pip_uuid),
            "name": row.pip_name,
            "version": row.pipeline_version,
        }
    if row.cn_id:
        context["connector"] = {
            "id": row.cn_id,
            "guid": GuidService.uuid_to_guid("con", row.cn_uuid),
            "name": row.cn_name,
        }

    bind.execute(sa.text("""
        UPDATE analysis_results
        SET target_entity_type = :tet, target_entity_id = :tei,
            target_entity_guid = :teg, target_entity_name = :ten,
            context_json = :ctx
        WHERE id = :id
    """), {
        "tet": "collection",
        "tei": row.collection_id,
        "teg": GuidService.uuid_to_guid("col", row.col_uuid),
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
        "teg": GuidService.uuid_to_guid("con", row.cn_uuid),
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
        "teg": GuidService.uuid_to_guid("pip", row.pip_uuid),
        "ten": row.pip_name,
        "id": row.id,
    })

# --- Backfill jobs ---

# 1. Collection-targeted jobs
# (same pattern as analysis_results — omitted for brevity)

# 2. Pipeline-targeted jobs (display_graph mode)
# (same pattern — omitted for brevity)

# 3. Connector-targeted jobs (inventory tools)
# Extract connector_id from progress_json
rows = bind.execute(sa.text("""
    SELECT j.id, j.progress_json
    FROM jobs j
    WHERE j.tool IN ('inventory_validate', 'inventory_import')
      AND j.target_entity_type IS NULL
""")).fetchall()

for row in rows:
    progress = json.loads(row.progress_json) if row.progress_json else {}
    connector_id = progress.get("connector_id")
    if not connector_id:
        continue  # Skip jobs with missing connector_id

    cn = bind.execute(sa.text(
        "SELECT id, uuid, name FROM connectors WHERE id = :cid"
    ), {"cid": connector_id}).fetchone()

    if not cn:
        continue  # Connector may have been deleted

    bind.execute(sa.text("""
        UPDATE jobs
        SET target_entity_type = :tet, target_entity_id = :tei,
            target_entity_guid = :teg, target_entity_name = :ten,
            context_json = NULL
        WHERE id = :id
    """), {
        "tet": "connector",
        "tei": cn.id,
        "teg": GuidService.uuid_to_guid("con", cn.uuid),
        "ten": cn.name,
        "id": row.id,
    })
```

#### Rollback

Drop the new columns and indexes. No data loss — legacy FK columns are untouched.

### Phase 2: Model + Service Layer — Dual Write (No New Migration)

Update all code paths to write **both** old FK columns AND new target/context columns:

- **Job creation**: `tool_service.py`, `inventory_service.py` set target + context based on tool type
- **Result creation**: `job_coordinator_service.py._create_result()` copies target + context from Job
- **Read paths**: Still use old FK columns (no risk)

This phase is pure code changes. If anything breaks, the old columns still work.

**Rollback**: Revert the service-layer commits. Legacy FK columns remain authoritative — reads never switched away from them. All writes still populate old FKs, so no data inconsistency.

### Phase 3: Switch Reads + Update API Schemas + Frontend

- **Backend reads**: Switch from FK-based queries to `target_entity_type + target_entity_id`
- **API responses**: Add `target: TargetEntityInfo` and `context: ResultContext` fields
- **Deprecated fields**: Keep `collection_guid`, `collection_name`, `connector_guid`, `connector_name`, `pipeline_guid`, `pipeline_name`, `pipeline_version` — populated from target/context for backward compat
- **Frontend**: Replace separate Collection/Connector columns in ResultsTable with unified "Target" column showing icon + name + navigation link. Show context (pipeline version, connector) as secondary info.

**Rollback**: Revert the read-switch and schema commits. Old FK columns are still being written (Phase 2 dual-write continues), so reverting reads to FK-based queries restores the previous behavior immediately. Deprecated API fields were still being populated, so frontend can fall back without changes.

### Phase 4: Drop Legacy FK Columns (Deferred — Separate Future PR)

Remove `collection_id`, `connector_id`, `pipeline_id`, `pipeline_version` from both models once Phase 3 is stable in production. This is a separate, clean PR with its own migration. Timeline: at least 2 releases after Phase 3 stabilizes.

## API Contract Changes

### New Shared Types

```python
# backend/src/schemas/target.py (NEW)

class TargetEntityInfo(BaseModel):
    """Primary target entity for a Job or AnalysisResult."""
    entity_type: TargetEntityType  # Enum, not plain str — enforces validation
    entity_guid: str               # col_xxx, con_xxx, pip_xxx
    entity_name: str | None

class ContextEntityRef(BaseModel):
    """Snapshot reference to a related entity in context."""
    guid: str
    name: str | None

class PipelineContextRef(ContextEntityRef):
    """Pipeline reference with version snapshot."""
    version: int | None

class ResultContext(BaseModel):
    """Execution context — secondary entity references."""
    pipeline: PipelineContextRef | None = None
    connector: ContextEntityRef | None = None
```

> **Reviewer feedback addressed**: `TargetEntityInfo.entity_type` uses the `TargetEntityType` enum (not a plain `str`) so Python validates the same literals as TypeScript.

### TypeScript Contracts

```typescript
// frontend/src/contracts/api/target-api.ts (NEW)

export type TargetEntityType = 'collection' | 'connector' | 'pipeline' | 'camera'

export interface TargetEntityInfo {
  entity_type: TargetEntityType
  entity_guid: string
  entity_name: string | null
}

export interface ContextEntityRef {
  guid: string
  name: string | null
}

export interface PipelineContextRef extends ContextEntityRef {
  version: number | null
}

export interface ResultContext {
  pipeline?: PipelineContextRef | null
  connector?: ContextEntityRef | null
}
```

### Response Schema Changes

**AnalysisResultSummary** and **AnalysisResultResponse**: Add `target` + `context` fields. Keep all existing fields as deprecated but functional.

**JobResponse**: Add `target` + `context` fields. Keep `collection_guid` and `pipeline_guid` as deprecated.

### Query Parameter Changes

**ResultsQueryParams**: Add `target_entity_type` filter (replaces the implicit collection-only filter).

## Frontend UI Changes

### ResultsTable — Unified Target Column

Replace the separate "Collection" and "Connector" columns with one **"Target"** column:

```text
Icon  Name (clickable link)    Context badge
────  ────────────────────    ──────────────
📁   Vacation 2024            via Standard RAW v3
📁   Card1-Import             via Standard RAW v3
🔌   AWS Production S3
🌿   Standard RAW Workflow
```

- Icon from domain icons (FolderOpen=Collection, Plug=Connector, GitBranch=Pipeline, Camera=Camera)
- Name links to the entity detail page
- "via Pipeline vN" badge shown when pipeline context exists

### ResultDetailPanel — Target + Context Section

- Header area: Target entity type icon + name (clickable link)
- Context section: "Pipeline: Standard RAW v3" (clickable) + "Connector: AWS Production" (clickable)

### Job Cards (AnalyticsPage Runs Tab)

- Show target entity name with icon and link instead of raw `collection_guid`
- Show pipeline context badge

## Agent Compatibility

**No agent binary changes required.**

The agent only interacts with the server via:
1. `POST /api/agent/v1/jobs/claim` — receives a Job (new fields are additive)
2. `POST /api/agent/v1/jobs/{guid}/complete` — sends results data, NOT target metadata

The server copies target + context from the Job to the AnalysisResult during `_create_result()`. The agent never needs to know about the polymorphic target pattern.

## Files to Modify

### New Files

| File | Purpose |
|------|---------|
| `backend/src/db/migrations/versions/072_polymorphic_target.py` | Alembic migration |
| `backend/src/schemas/target.py` | Shared target/context Pydantic schemas |
| `frontend/src/contracts/api/target-api.ts` | Shared target/context TypeScript types |

### Modified Files (Backend)

| File | Changes |
|------|---------|
| `backend/src/models/__init__.py` | Add `TargetEntityType` enum |
| `backend/src/models/analysis_result.py` | Add target + context columns, properties |
| `backend/src/models/job.py` | Add target + context columns, properties |
| `backend/src/services/job_coordinator_service.py` | Dual-write, unified _find_previous_result, eliminate progress_json connector hack |
| `backend/src/services/tool_service.py` | Set target + context on job creation |
| `backend/src/services/inventory_service.py` | Set target on inventory job creation |
| `backend/src/services/result_service.py` | Switch reads to target/context, remove N+1 joins |
| `backend/src/schemas/results.py` | Add target + context fields, target_entity_type filter |
| `backend/src/schemas/tools.py` | Add target + context to JobResponse |
| `backend/src/api/results.py` | Add target_entity_type query param |
| `backend/src/api/tools.py` | Populate target + context in JobResponse |

### Modified Files (Frontend)

| File | Changes |
|------|---------|
| `frontend/src/contracts/api/results-api.ts` | Import + add target/context to interfaces |
| `frontend/src/contracts/api/tools-api.ts` | Import + add target/context to Job interface |
| `frontend/src/components/results/ResultsTable.tsx` | Unified Target column with icon + link |
| `frontend/src/components/results/ResultDetailPanel.tsx` | Target + context in detail view |
| `frontend/src/pages/AnalyticsPage.tsx` | Target in job cards |

### Test Files

| Impact | Files |
|--------|-------|
| High | `conftest.py`, `test_job_coordinator.py`, `test_result_service.py`, `test_tool_service.py`, `test_inventory_service.py` |
| Medium | `test_tool_execution_flow.py`, `test_job_claim.py`, `test_api_results.py`, `test_api_tools.py` |

## Constitution Check

- [x] **Agent-Only Tool Execution (I)**: No changes to tool execution. Target metadata is server-side only.
- [x] **Testing & Quality (II)**: All modified services and APIs will have updated tests.
- [x] **User-Centric Design (III)**: UI improvements — entity names with links instead of raw GUIDs.
- [x] **Global Unique Identifiers (IV)**: GUIDs cached in `target_entity_guid` for API use. No numeric IDs exposed.
- [x] **Multi-Tenancy (V)**: `team_id` scoping unchanged. Target columns don't affect tenant isolation.
- [x] **Agent-Only Execution (VI)**: Server coordination unchanged. Agent API backward compatible.
- [x] **Audit Trail (VII)**: AuditMixin unchanged on both models.

## Verification Plan

1. **Migration roundtrip**: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
2. **Backfill verification** — assert zero unbackfilled rows in both tables:
   ```sql
   SELECT count(*) AS unbackfilled FROM analysis_results WHERE target_entity_type IS NULL;
   -- Expected: 0
   SELECT count(*) AS unbackfilled FROM jobs WHERE target_entity_type IS NULL;
   -- Expected: 0
   ```
3. **GUID format verification** — confirm backfilled GUIDs are properly encoded:
   ```sql
   SELECT target_entity_guid FROM analysis_results
   WHERE target_entity_guid NOT LIKE 'col_%'
     AND target_entity_guid NOT LIKE 'con_%'
     AND target_entity_guid NOT LIKE 'pip_%'
     AND target_entity_guid NOT LIKE 'cam_%'
     AND target_entity_type IS NOT NULL;
   -- Expected: 0 rows
   ```
4. **Context verification** — confirm collection-based results have pipeline context:
   ```sql
   SELECT count(*) FROM analysis_results
   WHERE target_entity_type = 'collection'
     AND pipeline_id IS NOT NULL
     AND (context_json IS NULL OR context_json::text NOT LIKE '%pipeline%');
   -- Expected: 0 (every result with a pipeline_id should have pipeline in context)
   ```
5. **Backend tests**: `venv/bin/python -m pytest backend/tests/ -v`
6. **Frontend type-check**: `cd frontend && npx tsc --noEmit`
7. **Smoke test**: Run each tool type (photostats, pipeline_validation collection + display_graph, inventory_validate), verify target + context in results table and detail panel
8. **Backward compat**: Verify deprecated `collection_guid`, `pipeline_guid` fields still populated in API responses

## Resolved Questions (from Rev 1 reviewer feedback)

1. **Backfill GUID encoding** — **Python iteration** (not SQL). Crockford Base32 is application logic in `GuidService`. SQL cannot encode it. Python iteration is dialect-agnostic, correct, and verifiable. Performance is acceptable for the current data volume.

2. **Phase 4 timeline** — **At least 2 releases** after Phase 3 stabilizes. Legacy FK columns are harmless to keep and provide a safety net.

3. **Context JSON schema validation** — **Application-level only** (Pydantic `exclude_none=True`). No DB-level CHECK constraint. The JSONB column is opaque to the database; all structure is enforced by the `ResultContext` Pydantic model on write.

4. **Name staleness** — **Point-in-time snapshots are the correct behavior**. The result was produced when the collection had that name. No background refresh task needed. If requirements change in the future, a refresh can be added independently.
