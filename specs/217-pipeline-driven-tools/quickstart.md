# Quickstart: Pipeline-Driven Analysis Tools

**Feature Branch**: `217-pipeline-driven-tools`

## Prerequisites

- Python 3.11+ with venv activated (`venv/bin/python`)
- Node.js 18+ with frontend dependencies installed
- PostgreSQL running (or SQLite for tests)
- Existing Pipeline with Capture, File, and Process nodes

## Development Setup

```bash
# Activate venv
source venv/bin/activate

# Run backend tests
venv/bin/python -m pytest backend/tests/unit/ -v

# Run agent tests
venv/bin/python -m pytest agent/tests/ -v

# Run frontend type checking
cd frontend && npx tsc --noEmit

# Run frontend tests
cd frontend && npx vitest run
```

## Key Files to Understand First

### Agent (Pipeline extraction + tool integration)

1. **`agent/src/analysis/pipeline_tool_config.py`** (NEW)
   - `PipelineToolConfig` dataclass
   - `extract_tool_config(nodes_json, edges_json)` → extracts extensions, regex, suffixes, sidecar rules
   - Start here to understand what the Pipeline provides to tools

2. **`agent/src/analysis/pipeline_config_builder.py`** (EXISTING)
   - `build_pipeline_config()` — parses raw JSON into typed node objects
   - Foundation for `extract_tool_config()`

3. **`agent/cli/run.py`** (MODIFIED)
   - `_execute_tool()` — dispatches to tool functions with Pipeline or Config params
   - `_run_photo_pairing()` — gains Pipeline regex, camera discovery, processing suffixes
   - Pipeline resolution: Collection pipeline → team default → Config fallback

### Backend (Camera entity + API)

4. **`backend/src/models/camera.py`** (NEW)
   - `Camera` model with `ExternalIdMixin` + `AuditMixin`
   - GUID prefix `cam_`

5. **`backend/src/services/camera_service.py`** (NEW)
   - CRUD + `discover_cameras()` (idempotent batch creation)
   - DB-agnostic check-before-insert pattern

6. **`backend/src/api/cameras.py`** (NEW)
   - User-facing CRUD endpoints at `/api/cameras`

7. **`backend/src/api/agent/camera_routes.py`** (NEW)
   - Agent-facing `POST /api/agent/v1/cameras/discover`

### Frontend (Resources page)

8. **`frontend/src/pages/ResourcesPage.tsx`** (NEW)
   - Tabbed page: Cameras + Pipelines
   - Follows `DirectoryPage.tsx` pattern

9. **`frontend/src/components/cameras/CamerasTab.tsx`** (NEW)
   - Camera list with status filter, edit dialog

10. **`frontend/src/components/pipelines/PipelinesTab.tsx`** (NEW)
    - Extracted from `PipelinesPage.tsx` — all Pipeline functionality preserved

## Implementation Order

```
Phase 1: PipelineToolConfig extraction + Camera entity + API
    ↓
Phase 2: PhotoStats Pipeline integration
    ↓
Phase 3: Photo_Pairing Pipeline integration + Camera discovery
    ↓
Phase 4: Agent Pipeline resolution + offline caching
    ↓
Phase 5: Frontend Resources page + Camera management UI
```

Each phase is independently testable and deployable.

## Testing Strategy

### Agent tests (`agent/tests/`)
- `test_pipeline_tool_config.py` — extraction from various Pipeline structures
- `test_camera_discovery.py` — agent-side discovery function (mock HTTP)

### Backend tests (`backend/tests/unit/`)
- `test_camera_service.py` — CRUD, discover, idempotency, cross-team isolation
- `test_camera_api.py` — endpoint HTTP tests

### Frontend tests (`frontend/src/`)
- `hooks/__tests__/useCameras.test.tsx` — data fetching hooks
- Component tests for CamerasTab, ResourcesPage

## Quick Verification

After implementing Phase 1, verify with:

```bash
# Camera service tests
venv/bin/python -m pytest backend/tests/unit/test_camera_service.py -v

# PipelineToolConfig extraction tests
venv/bin/python -m pytest agent/tests/unit/test_pipeline_tool_config.py -v

# Camera API endpoints
venv/bin/python -m pytest backend/tests/unit/test_camera_api.py -v
```
