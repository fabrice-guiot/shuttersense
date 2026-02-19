# Implementation Plan: Polymorphic Target Entity for Job & AnalysisResult

**Branch**: `110-polymorphic-results` | **Date**: 2026-02-19 | **Issue**: [#110](https://github.com/fabrice-guiot/shuttersense/issues/110)
**Status**: Draft — awaiting reviewer feedback

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

```
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
context_json        JSONB         -- structured context (see below)
```

### Context JSON Structure

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

Context is a **point-in-time snapshot**:
- Even if a pipeline is renamed or deleted, the context preserves what was used at execution time
- This is _better_ than the current FK-with-SET-NULL behavior, which loses pipeline references on delete
- No JOINs needed to resolve names in list views — guid and name are cached

### Target Entity Type Enum

```python
class TargetEntityType(str, enum.Enum):
    COLLECTION = "collection"
    CONNECTOR = "connector"
    PIPELINE = "pipeline"
    # Future (no schema change needed):
    # CAMERA = "camera"
    # ALBUM = "album"
    # EVENT = "event"
    # WORKFLOW = "workflow"
```

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

**Migration**: `072_polymorphic_target.py` (≤32 char revision ID)

**Operations**:
1. Add 5 columns to `analysis_results` (all nullable)
2. Add 5 columns to `jobs` (all nullable)
3. Create composite indexes:
   - `idx_results_target (target_entity_type, target_entity_id)`
   - `idx_results_target_tool (target_entity_type, target_entity_id, tool, created_at DESC)`
   - `idx_jobs_target (target_entity_type, target_entity_id)`
4. Backfill existing records (dialect-aware SQL for PostgreSQL + SQLite):

**analysis_results backfill**:
```sql
-- Collection-targeted results
UPDATE analysis_results ar
SET target_entity_type = 'collection',
    target_entity_id = ar.collection_id,
    target_entity_guid = c.uuid,  -- will need GUID computation
    target_entity_name = c.name,
    context_json = json_build_object(
      'pipeline', CASE WHEN ar.pipeline_id IS NOT NULL THEN
        json_build_object('id', ar.pipeline_id, 'guid', p.uuid, 'name', p.name, 'version', ar.pipeline_version)
      ELSE NULL END,
      'connector', CASE WHEN c.connector_id IS NOT NULL THEN
        json_build_object('id', cn.id, 'guid', cn.uuid, 'name', cn.name)
      ELSE NULL END
    )
FROM collections c
LEFT JOIN pipelines p ON ar.pipeline_id = p.id
LEFT JOIN connectors cn ON c.connector_id = cn.id
WHERE ar.collection_id = c.id AND ar.collection_id IS NOT NULL;

-- Connector-targeted results (inventory tools)
UPDATE analysis_results ar
SET target_entity_type = 'connector',
    target_entity_id = ar.connector_id,
    target_entity_guid = cn.uuid,
    target_entity_name = cn.name
FROM connectors cn
WHERE ar.connector_id = cn.id AND ar.collection_id IS NULL;

-- Pipeline-targeted results (display_graph)
UPDATE analysis_results ar
SET target_entity_type = 'pipeline',
    target_entity_id = ar.pipeline_id,
    target_entity_guid = p.uuid,
    target_entity_name = p.name
FROM pipelines p
WHERE ar.pipeline_id = p.id AND ar.collection_id IS NULL AND ar.connector_id IS NULL;
```

**jobs backfill**: Similar pattern. For inventory jobs, extract `connector_id` from `progress_json`.

**Note on GUID computation**: The backfill needs to convert UUIDs to GUID format (`prefix_crockfordbase32`). This may need to be done in Python (iterate rows) rather than pure SQL, since Crockford Base32 encoding is application logic. Alternatively, store the raw UUID temporarily and fix GUIDs in Phase 2 Python code.

**Rollback**: Drop the new columns and indexes.

### Phase 2: Model + Service Layer — Dual Write (No New Migration)

Update all code paths to write **both** old FK columns AND new target/context columns:

- **Job creation**: `tool_service.py`, `inventory_service.py` set target + context based on tool type
- **Result creation**: `job_coordinator_service.py._create_result()` copies target + context from Job
- **Read paths**: Still use old FK columns (no risk)

This phase is pure code changes. If anything breaks, the old columns still work.

### Phase 3: Switch Reads + Update API Schemas + Frontend

- **Backend reads**: Switch from FK-based queries to `target_entity_type + target_entity_id`
- **API responses**: Add `target: TargetEntityInfo` and `context: ResultContext` fields
- **Deprecated fields**: Keep `collection_guid`, `collection_name`, `connector_guid`, `connector_name`, `pipeline_guid`, `pipeline_name`, `pipeline_version` — populated from target/context for backward compat
- **Frontend**: Replace separate Collection/Connector columns in ResultsTable with unified "Target" column showing icon + name + navigation link. Show context (pipeline version, connector) as secondary info.

### Phase 4: Drop Legacy FK Columns (Deferred — Separate Future PR)

Remove `collection_id`, `connector_id`, `pipeline_id`, `pipeline_version` from both models once Phase 3 is stable in production. This is a separate, clean PR with its own migration.

## API Contract Changes

### New Shared Types

```python
# backend/src/schemas/target.py (NEW)

class TargetEntityInfo(BaseModel):
    """Primary target entity for a Job or AnalysisResult."""
    entity_type: str       # "collection", "connector", "pipeline"
    entity_guid: str       # col_xxx, con_xxx, pip_xxx
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

### TypeScript Contracts

```typescript
// frontend/src/contracts/api/target-api.ts (NEW)

export interface TargetEntityInfo {
  entity_type: 'collection' | 'connector' | 'pipeline' | 'camera'
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

```
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
2. **Backfill verification**: `SELECT target_entity_type, count(*) FROM analysis_results GROUP BY 1` — no NULLs
3. **Context verification**: Spot-check collection-based results have pipeline guid/name/version in context_json
4. **Backend tests**: `venv/bin/python -m pytest backend/tests/ -v`
5. **Frontend type-check**: `cd frontend && npx tsc --noEmit`
6. **Smoke test**: Run each tool type (photostats, pipeline_validation collection + display_graph, inventory_validate), verify target + context in results table and detail panel
7. **Backward compat**: Verify deprecated `collection_guid`, `pipeline_guid` fields still populated in API responses

## Open Questions for Reviewers

1. **Backfill GUID encoding**: Should the migration compute Crockford Base32 GUIDs in SQL or iterate in Python? SQL is faster but complex; Python is cleaner but slower for large datasets.

2. **Phase 4 timeline**: When should we drop the legacy FK columns? Options: (a) next release after Phase 3 stabilizes, (b) after 2 releases, (c) never (keep for safety net).

3. **Context JSON schema validation**: Should we enforce a JSON schema on `context_json` at the DB level (CHECK constraint) or only at the application level (Pydantic)? Application-level is simpler and sufficient for type safety.

4. **Name staleness**: Should we add a background task to refresh cached `target_entity_name` when entities are renamed, or accept point-in-time snapshots as the correct behavior?
