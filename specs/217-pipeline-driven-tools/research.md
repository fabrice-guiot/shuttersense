# Research: Pipeline-Driven Analysis Tools

**Feature Branch**: `217-pipeline-driven-tools`
**Date**: 2026-02-17

## Research Tasks & Findings

### R1: Pipeline Node Structure and Properties

**Question**: What are the exact node types, properties, and edge formats used by `build_pipeline_config()`?

**Decision**: Use existing `PipelineConfig` infrastructure from `pipeline_config_builder.py` as the foundation for `PipelineToolConfig` extraction.

**Findings**:

Node types and their dataclass representations (from `utils/pipeline_processor.py`):

| Node Type | Class | Key Properties |
|-----------|-------|---------------|
| `capture` | `CaptureNode` | `name` (from properties or node-level) |
| `file` | `FileNode` | `extension` (e.g., `.cr3`, `.xmp`) |
| `process` | `ProcessNode` | `method_ids: List[str]` (e.g., `["HDR"]`) |
| `pairing` | `PairingNode` | `pairing_type`, `input_count` |
| `branching` | `BranchingNode` | `condition_description` |
| `termination` | `TerminationNode` | `termination_type` |

All inherit from `NodeBase(id, name, output: List[str])`.

**Capture node properties** (stored in `nodes_json[].properties`):
- `sample_filename`: Required. Used for validation.
- `filename_regex`: Required. Must have exactly 2 capture groups. Validated by `_validate_capture_node_properties()`.
- `camera_id_group`: `"1"` or `"2"`. Determines which capture group is the camera ID.

**Edge JSON format**: `{"from": "node_id", "to": "node_id"}` — builder also handles `source`/`target` aliases.

**File node `optional` property**: Stored as `properties.optional: bool` (not on the FileNode dataclass). Must be read from raw `nodes_json` for sidecar inference.

**Rationale**: Reusing `build_pipeline_config()` avoids duplicating node parsing logic. The builder handles all naming conventions (camelCase/snake_case) and edge format variations.

**Alternatives considered**:
- Parse `nodes_json` directly without `build_pipeline_config()` → Rejected: would duplicate format handling and break if node parsing changes.

---

### R2: Agent Tool Execution Flow and Config Resolution

**Question**: How do tools currently receive configuration, and where should `PipelineToolConfig` be injected?

**Decision**: Add `pipeline_tool_config: Optional[PipelineToolConfig] = None` parameter to `_execute_tool()` and resolve it in the `run()` command after `resolve_team_config()`.

**Findings**:

Current flow in `agent/cli/run.py`:
1. `resolve_team_config()` → `ConfigResult(config: TeamConfigCache, source: str)`
2. `_prepare_analysis(location, tool, team_config)` → `(file_infos, input_state_hash)`
3. `_execute_tool(tool, file_infos, location, team_config)` → `(data, html)`

`_execute_tool()` converts `TeamConfigCache` lists to sets:
```python
photo_extensions = set(team_config.photo_extensions)
metadata_extensions = set(team_config.metadata_extensions)
require_sidecar = set(team_config.require_sidecar)
```

Then dispatches to:
- `_run_photostats(file_infos, photo_extensions, metadata_extensions, require_sidecar, location)`
- `_run_photo_pairing(file_infos, photo_extensions, location)` — note: no metadata_extensions or processing config passed
- `_run_pipeline_validation(file_infos, photo_extensions, metadata_extensions, team_config, location)` — gets full team_config for pipeline access

**Key gap**: `_run_photo_pairing()` calls `calculate_analytics(imagegroups, {})` with empty config — camera names and processing methods are never resolved.

**Injection point**: After `resolve_team_config()`, before `_prepare_analysis()`:
1. Resolve Pipeline: `Collection.pipeline_id` → specific Pipeline, or `team_config.default_pipeline` → team default, or None → Config fallback
2. Extract: `pipeline_tool_config = extract_tool_config(pipeline.nodes, pipeline.edges)`
3. Pass to `_execute_tool()` alongside `team_config`

**Rationale**: Minimal change to existing flow. Pipeline resolution is a new step inserted between config resolution and tool execution.

---

### R3: `build_imagegroups()` and Filename Parsing

**Question**: How does `build_imagegroups()` currently parse filenames, and how should Pipeline regex be integrated?

**Decision**: Add optional `filename_regex` and `camera_id_group` parameters to `build_imagegroups()`. When provided, use regex; otherwise fall back to `FilenameParser`.

**Findings**:

Current signature: `build_imagegroups(files: List[FileInfo]) -> Dict[str, Any]`

Uses `FilenameParser.validate_filename()` and `FilenameParser.parse_filename()` with hardcoded pattern `[A-Z0-9]{4}[0-9]{4}`.

Returns: `{"imagegroups": [...], "invalid_files": [...]}`

Each imagegroup: `{"group_id", "camera_id", "counter", "separate_images": {...}}`

**Integration plan**:
- New signature: `build_imagegroups(files, filename_regex=None, camera_id_group=None)`
- When `filename_regex` provided: use `re.match(filename_regex, stem)` to extract camera_id and counter from capture groups
- When None: fall back to existing `FilenameParser` logic
- Numeric suffix detection (`-2`, `-3`) remains hardcoded regardless of source

**Rationale**: Adding optional parameters preserves backward compatibility. All existing callers continue to work without changes.

---

### R4: ExternalIdMixin vs GuidMixin Pattern

**Question**: Which mixin should Camera use for GUID generation?

**Decision**: Use `ExternalIdMixin` with `GUID_PREFIX = "cam"`, matching the PRD specification.

**Findings**:

Looking at the codebase, `GuidMixin` (from `backend/src/models/mixins/guid.py`) provides:
- `uuid` column (UUIDv7)
- `guid` property (computed: `{prefix}_{crockford_base32(uuid)}`)
- `GUID_PREFIX` class variable

`ExternalIdMixin` (from `backend/src/models/mixins/external_id.py`) provides the same interface but with a different internal implementation. The PRD explicitly states `ExternalIdMixin`.

Existing entities use `GuidMixin` (Pipeline, Collection, etc.). The `ExternalIdMixin` pattern appears to be newer.

**Rationale**: Follow PRD recommendation. Both produce the same GUID format externally.

---

### R5: TeamConfigCache and Offline Pipeline Caching

**Question**: How should Pipeline data be cached for offline mode?

**Decision**: `TeamConfigCache` already includes `default_pipeline: Optional[CachedPipeline]` with `nodes` and `edges`. Extend to optionally include collection-specific Pipeline data.

**Findings**:

`CachedPipeline` model:
```python
class CachedPipeline(BaseModel):
    guid: str
    name: str
    version: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
```

`TeamConfigCache` already stores `default_pipeline`. For collection-specific pipelines, the agent can cache the assigned pipeline alongside the team config during the `get_team_config()` call, or fetch it separately via the collection's pipeline data.

**Rationale**: Minimal cache format change. The existing `CachedPipeline` structure already has all fields needed for `extract_tool_config()`.

---

### R6: Frontend Tabbed Page Pattern

**Question**: What is the exact pattern for URL-synced tabbed pages?

**Decision**: Follow the `DirectoryPage.tsx` pattern exactly: `useSearchParams` for tab sync, `TABS` constant array, per-tab KPI stats via `useHeaderStats`.

**Findings**:

Pattern from `DirectoryPage.tsx`:
```typescript
const TABS = [
  { id: 'locations', label: 'Locations', icon: MapPin },
  { id: 'organizers', label: 'Organizers', icon: Building2 },
  { id: 'performers', label: 'Performers', icon: Users },
] as const

type TabId = typeof TABS[number]['id']
const DEFAULT_TAB: TabId = 'locations'

const [searchParams, setSearchParams] = useSearchParams()
const currentTab = (searchParams.get('tab') as TabId) || DEFAULT_TAB

const handleTabChange = (value: string) => {
  setSearchParams({ tab: value }, { replace: true })
}
```

Each tab component manages its own `useHeaderStats().setStats()` call, setting domain-specific KPIs and clearing on unmount.

Action buttons follow the responsive pattern: `flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between`.

**Rationale**: Proven pattern already used in the codebase. Consistent UX across Directory and Resources pages.

---

### R7: Camera CRUD API Patterns

**Question**: What patterns do existing entity APIs follow for CRUD, stats, and list endpoints?

**Decision**: Follow the Pipeline API pattern: service class with CRUD methods, Pydantic schemas for request/response, router with `TenantContext` dependency.

**Findings**:

Standard pattern from Pipeline and other entities:
- **Service**: `CameraService(db: Session)` with `list()`, `get_by_guid()`, `create()`, `update()`, `delete()`, `get_stats()`, `discover_cameras()`
- **Schemas**: `CameraResponse`, `CameraCreateRequest`, `CameraUpdateRequest`, `CameraStatsResponse`, `CameraDiscoverRequest`, `CameraDiscoverResponse`
- **Router**: `/api/cameras` with `TenantContext` dependency for all endpoints
- **Agent router**: `/api/agent/v1/cameras/discover` with `get_authenticated_agent` dependency

List endpoint supports: pagination (`limit`, `offset`), filtering (`status`), search.

**Rationale**: Consistent with all existing entity APIs in the codebase. No novel patterns needed.

---

### R8: DB-Agnostic Camera Discovery

**Question**: How to implement idempotent camera creation that works on both PostgreSQL and SQLite?

**Decision**: Use check-before-insert within the same transaction, with `IntegrityError` catch as safety net for race conditions.

**Findings**:

Pattern from PRD:
```python
for camera_id in camera_ids:
    existing = self.db.query(Camera).filter_by(team_id=team_id, camera_id=camera_id).first()
    if existing:
        results.append(existing)
    else:
        try:
            camera = Camera(team_id=team_id, camera_id=camera_id, status="temporary", ...)
            self.db.add(camera)
            self.db.flush()
            results.append(camera)
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(Camera).filter_by(...).first()
            results.append(existing)
```

This avoids PostgreSQL-specific `INSERT ... ON CONFLICT` which doesn't work on SQLite. The unique constraint `(team_id, camera_id)` provides the safety net.

**Rationale**: Tests run on SQLite, production on PostgreSQL. DB-agnostic pattern ensures both work identically.

**Alternatives considered**:
- `INSERT ... ON CONFLICT DO NOTHING` → Rejected: PostgreSQL-specific, breaks SQLite tests
- `session.merge()` → Rejected: requires natural key mapping, more complex than check-before-insert

---

### R9: PipelinesPage Refactoring Strategy

**Question**: How to refactor PipelinesPage into PipelinesTab without losing functionality?

**Decision**: Extract the body of `PipelinesPage` into a `PipelinesTab` component. The tab receives no special props — it manages its own data fetching, actions, and modals internally.

**Findings**:

`PipelinesPage` manages:
- `usePipelines({ autoFetch: true })` — list, CRUD, activate/deactivate, set/unset default
- `usePipelineStats(true)` — TopHeader KPIs
- `usePipelineExport()` / `usePipelineImport()` — YAML import/export
- Hidden file input ref for import
- Multiple confirmation modals (delete, activate, deactivate, set/unset default)
- Navigation to `/pipelines/new`, `/pipelines/{guid}`, `/pipelines/{guid}/edit`

The tab component will be a near-copy of the page body, with:
- Same hooks and state management
- Same action handlers (navigate to `/pipelines/new` etc. — routes still work)
- Same confirmation modals
- Own `useHeaderStats().setStats()` for Pipeline KPIs (set when tab active, cleared on unmount)

**Rationale**: Minimal refactoring risk. The tab is self-contained and manages all Pipeline functionality internally, just like `LocationsTab` manages all Location functionality.
