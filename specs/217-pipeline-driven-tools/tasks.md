# Tasks: Pipeline-Driven Analysis Tools

**Input**: Design documents from `/specs/217-pipeline-driven-tools/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included as they are explicitly required by the spec (NFR-400) and PRD.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Agent**: `agent/src/`, `agent/cli/`, `agent/tests/`
- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — create the Camera entity and PipelineToolConfig extraction that all stories depend on.

- [x] T001 Create `PipelineToolConfig` dataclass and `METADATA_EXTENSIONS` constant in `agent/src/analysis/pipeline_tool_config.py`
- [x] T002 Implement `extract_tool_config(nodes_json, edges_json)` in `agent/src/analysis/pipeline_tool_config.py` — extract filename_regex, camera_id_group, photo/metadata extensions, processing_suffixes from Pipeline nodes using `build_pipeline_config()`
- [x] T003 Implement `_infer_sidecar_requirements()` helper in `agent/src/analysis/pipeline_tool_config.py` — infer require_sidecar from sibling File nodes (non-optional metadata + image under same parent)
- [ ] T004 [P] Create `Camera` model in `backend/src/models/camera.py` using `GuidMixin` + `AuditMixin` with GUID prefix `cam_`, unique constraint `(team_id, camera_id)`
- [ ] T005 [P] Add reciprocal `cameras` relationship to `Team` model in `backend/src/models/team.py`
- [ ] T006 Create Alembic migration for `cameras` table in `backend/alembic/versions/`
- [ ] T007 [P] Create Camera Pydantic schemas in `backend/src/schemas/camera.py` — `CameraResponse`, `CameraUpdateRequest`, `CameraStatsResponse`, `CameraDiscoverRequest`, `CameraDiscoverResponse`
- [ ] T008 Create `CameraService` in `backend/src/services/camera_service.py` — `list()`, `get_by_guid()`, `create()`, `update()`, `delete()`, `get_stats()`, `discover_cameras()` with DB-agnostic check-before-insert pattern
- [ ] T009 [P] Create user-facing Camera API endpoints in `backend/src/api/cameras.py` — `GET /api/cameras`, `GET /api/cameras/stats`, `GET /api/cameras/{guid}`, `PUT /api/cameras/{guid}`, `DELETE /api/cameras/{guid}` with TenantContext
- [ ] T010 [P] Create agent-facing Camera discovery endpoint in `backend/src/api/agent/camera_routes.py` — `POST /api/agent/v1/cameras/discover` with agent authentication
- [ ] T011 Register Camera API routers in `backend/src/api/__init__.py` (user-facing) and `backend/src/api/agent/__init__.py` (agent-facing)
- [x] T012 [P] Add `discover_cameras(camera_ids, timeout)` method to `AgentApiClient` in `agent/src/api_client.py` — POST to `/api/agent/v1/cameras/discover`

### Setup Tests

- [x] T013 [P] Unit tests for `extract_tool_config()` in `agent/tests/unit/test_pipeline_tool_config.py` — linear pipeline, branching, multi-file, missing capture node error, sidecar inference with optional/non-optional metadata, extension case-insensitivity, deterministic output, multiple Capture nodes (uses first), File node without extension property (skipped)
- [ ] T014 [P] Unit tests for `CameraService` in `backend/tests/unit/test_camera_service.py` — CRUD, discover (idempotent creation, skip existing), concurrent discover (IntegrityError handling), cross-team isolation, stats
- [ ] T015 [P] Unit tests for Camera API endpoints in `backend/tests/unit/test_camera_api.py` — list (paginated, filtered), get by GUID, update, delete, stats, 404 for unknown/cross-team
- [ ] T016 [P] Unit tests for agent-facing discover endpoint in `backend/tests/unit/test_camera_discover_api.py` — batch discover, idempotent, empty list
- [x] T017 [P] Unit tests for `AgentApiClient.discover_cameras()` in `agent/tests/unit/test_api_client_discover.py` — mock HTTP, verify request shape and response parsing

**Checkpoint**: `PipelineToolConfig` extraction works for all Pipeline structures. Camera entity exists with full CRUD API and agent discovery endpoint. All setup tests pass.

---

## Phase 2: User Story 1 — Pipeline-Derived Extensions for PhotoStats (Priority: P1) MVP

**Goal**: PhotoStats uses Pipeline-derived image/metadata extensions and sidecar requirements instead of Config entries when a Pipeline is available.

**Independent Test**: Run PhotoStats on a Collection with an assigned Pipeline defining specific File nodes. Verify the tool uses Pipeline-derived extensions and ignores Config entries. Verify fallback to Config when no Pipeline is available.

### Implementation for User Story 1

- [ ] T018 [US1] Modify `_execute_tool()` in `agent/cli/run.py` to accept optional `pipeline_tool_config: Optional[PipelineToolConfig]` parameter and derive extensions from it when provided, falling back to `TeamConfigCache` when None
- [ ] T019 [US1] Modify `_run_photostats()` in `agent/cli/run.py` to accept Pipeline-derived `photo_extensions`, `metadata_extensions`, and `require_sidecar` sets (no signature change needed — already receives sets from `_execute_tool()`)
- [ ] T020 [US1] Add Pipeline resolution logic in agent `run()` command in `agent/cli/run.py` — resolve Collection pipeline_id → team default → Config fallback, call `extract_tool_config()`, handle ValueError with warning and fallback
- [ ] T021 [US1] Unit tests for PhotoStats Pipeline integration in `agent/tests/unit/test_photostats_pipeline.py` — verify identical results with Pipeline-derived vs Config-based extensions, verify fallback when no Pipeline, verify invalid Pipeline logs warning and falls back

**Checkpoint**: PhotoStats uses Pipeline-derived extensions when available, falls back to Config gracefully. All US1 tests pass.

---

## Phase 3: User Story 2 — Pipeline-Driven Filename Parsing for Photo_Pairing (Priority: P2)

**Goal**: Photo_Pairing uses the Pipeline Capture node's `filename_regex` for camera ID and counter extraction and Pipeline Process node names for processing method resolution.

**Independent Test**: Run Photo_Pairing on a Collection with a Pipeline whose Capture node defines a custom regex. Verify filenames are parsed correctly using the regex. Verify processing method names are resolved from Process node names.

### Implementation for User Story 2

- [ ] T022 [US2] Extend `build_imagegroups()` in `agent/src/analysis/photo_pairing_analyzer.py` to accept optional `filename_regex: str` and `camera_id_group: int` parameters — use regex when provided, fall back to `FilenameParser` when None
- [ ] T023 [US2] Modify `_run_photo_pairing()` in `agent/cli/run.py` to accept `pipeline_tool_config` and `http_client` parameters, pass `filename_regex` and `camera_id_group` to `build_imagegroups()`, pass `processing_suffixes` to `calculate_analytics()`
- [ ] T024 [US2] Wire `PipelineToolConfig` into Photo_Pairing execution path in `_execute_tool()` in `agent/cli/run.py` — pass `pipeline_tool_config` and `http_client` to `_run_photo_pairing()`
- [ ] T025 [US2] Unit tests for regex-based filename parsing in `agent/tests/unit/test_photo_pairing_pipeline.py` — custom regex patterns, camera_id_group=1 and =2, fallback to FilenameParser when no regex, processing suffix resolution from Pipeline, all-numeric suffix detection unchanged, verify Pipeline-derived photo_extensions used for file filtering (FR-011)

**Checkpoint**: Photo_Pairing uses Pipeline regex for parsing and Pipeline Process names for method resolution. All US2 tests pass.

---

## Phase 4: User Story 3 — Camera Auto-Discovery During Analysis (Priority: P3)

**Goal**: When Photo_Pairing encounters unknown camera IDs during analysis, the agent calls the discovery endpoint to auto-create Camera records and resolves display names for reports.

**Independent Test**: Run Photo_Pairing (online mode) on a Collection with known and unknown camera IDs. Verify new Camera records are created with `status: "temporary"`. Verify the report shows resolved names for known cameras and raw IDs for new ones. Verify offline mode skips discovery gracefully.

### Implementation for User Story 3

- [ ] T026 [US3] Implement `_discover_cameras()` function in `agent/cli/run.py` — extract unique camera IDs from imagegroups, call `http_client.discover_cameras()`, build camera_id→display_name mapping, handle offline (None client) and network errors with identity mapping fallback and warning log
- [ ] T027 [US3] Integrate Camera discovery into `_run_photo_pairing()` in `agent/cli/run.py` — call `_discover_cameras()` after `build_imagegroups()`, pass resolved camera names to `calculate_analytics()` via config dict
- [ ] T028 [US3] Unit tests for Camera auto-discovery in `agent/tests/unit/test_camera_discovery.py` — online discovery (mock HTTP), offline fallback (None client), network error fallback, empty camera list, duplicate camera IDs deduplication

**Checkpoint**: Camera auto-discovery creates records for new cameras during online analysis and falls back gracefully offline. All US3 tests pass.

---

## Phase 5: User Story 4 — Camera Management in the Resources Page (Priority: P4)

**Goal**: A "Resources" page consolidates Camera management and Pipeline management under tabs, replacing the standalone Pipelines page.

**Independent Test**: Navigate to `/resources`. Verify Cameras tab shows camera list with status filter. Verify editing a temporary camera. Verify Pipelines tab preserves all existing Pipeline functionality. Verify `/pipelines` redirects to `/resources?tab=pipelines`.

### Implementation for User Story 4

- [ ] T029 [P] [US4] Create Camera TypeScript contracts in `frontend/src/contracts/api/camera-api.ts` — `CameraResponse`, `CameraUpdateRequest`, `CameraStatsResponse`, `CameraDiscoverRequest`, `CameraDiscoverResponse`, `CameraListQueryParams`
- [ ] T030 [P] [US4] Create Camera API service in `frontend/src/services/cameras.ts` — `listCameras()`, `getCamera()`, `updateCamera()`, `deleteCamera()`, `getCameraStats()`
- [ ] T031 [US4] Create `useCameras` hook and `useCameraStats` hook in `frontend/src/hooks/useCameras.ts` — following `usePipelines` pattern with autoFetch, CRUD callbacks, stats
- [ ] T032 [P] [US4] Create `CameraList` component in `frontend/src/components/cameras/CameraList.tsx` — table with columns Camera ID, Display Name, Make, Model, Status (badge), Modified (AuditTrailPopover), edit/delete actions
- [ ] T033 [P] [US4] Create `CameraEditDialog` component in `frontend/src/components/cameras/CameraEditDialog.tsx` — Dialog for updating camera details (status, display_name, make, model, serial_number, notes)
- [ ] T034 [US4] Create `CamerasTab` component in `frontend/src/components/cameras/CamerasTab.tsx` — Camera list with search, status filter (All/Temporary/Confirmed), edit dialog, pagination, TopHeader stats via `useCameraStats`
- [ ] T035 [US4] Refactor `PipelinesPage` into `PipelinesTab` component in `frontend/src/components/pipelines/PipelinesTab.tsx` — extract page body into tab component, preserve all Pipeline functionality (list, CRUD, activate, validate, import/export, modals), manage own TopHeader stats
- [ ] T036 [US4] Create `ResourcesPage` in `frontend/src/pages/ResourcesPage.tsx` — URL-synced tabs (Cameras default, Pipelines) using `useSearchParams`, following `DirectoryPage.tsx` pattern
- [ ] T037 [US4] Update route configuration in `frontend/src/App.tsx` — add `/resources` route with `pageTitle: 'Resources'`, `pageIcon: Box`, `pageHelp`; add exact-match `/pipelines` redirect to `/resources?tab=pipelines` (keep existing `/pipelines/new`, `/pipelines/{guid}`, `/pipelines/{guid}/edit` routes unchanged)
- [ ] T038 [US4] Update sidebar menu in `frontend/src/components/layout/Sidebar.tsx` — replace "Pipelines" entry with "Resources" (`Box` icon, `/resources` href)
- [ ] T039 [US4] Frontend tests for Camera hooks in `frontend/src/hooks/__tests__/useCameras.test.tsx` — fetch, CRUD, stats, error handling

- [ ] T040 [P] [US4] Component tests for `ResourcesPage` in `frontend/src/pages/__tests__/ResourcesPage.test.tsx` — tab rendering, URL-synced tab switching via searchParams, default tab is Cameras, exact-match `/pipelines` redirect
- [ ] T041 [P] [US4] Component tests for `CamerasTab` in `frontend/src/components/cameras/__tests__/CamerasTab.test.tsx` — list renders with correct columns (Camera ID, Display Name, Make, Model, Status badge, Modified), status filter (All/Temporary/Confirmed), edit dialog opens and submits, delete confirmation, per-tab KPI stats in TopHeader
- [ ] T042 [P] [US4] Regression tests for `PipelinesTab` in `frontend/src/components/pipelines/__tests__/PipelinesTab.test.tsx` — list rendering, CRUD actions, activate/deactivate, set/unset default, validate, import/export, confirmation modals, per-tab KPI stats — all preserved after refactoring from PipelinesPage

**Checkpoint**: Resources page renders with Cameras and Pipelines tabs. Camera CRUD works. Pipeline functionality preserved. `/pipelines` redirects correctly. All US4 tests pass.

---

## Phase 6: User Story 5 — Pipeline Resolution per Collection (Priority: P5)

**Goal**: The Pipeline used for analysis is resolved per Collection: Collection-specific → team default → Config fallback. Offline mode uses cached Pipeline data.

**Independent Test**: Configure two Collections (one with assigned Pipeline, one without). Run analysis on each. Verify the correct Pipeline is used. Verify offline mode uses cached Pipeline. Verify invalid Pipeline falls back to Config with warning.

### Implementation for User Story 5

- [ ] T043 [US5] Implement `_resolve_collection_pipeline()` in `agent/cli/run.py` — resolve Collection.pipeline_id → specific Pipeline, then team default, then None for Config fallback; handle fetching Collection-specific pipeline from server or cache
- [ ] T044 [US5] Update `_prepare_analysis()` in `agent/cli/run.py` to include Pipeline data in `input_state_hash` computation when `PipelineToolConfig` is available (ensures hash changes when Pipeline changes)
- [ ] T045 [US5] Handle offline mode Pipeline caching — ensure `TeamConfigCache` includes Collection-assigned pipeline data when fetched from server, and `_resolve_collection_pipeline()` can use cached data when offline
- [ ] T046 [US5] Unit tests for Pipeline resolution in `agent/tests/unit/test_pipeline_resolution.py` — collection-specific pipeline, team default fallback, Config fallback, invalid pipeline warning + fallback, offline with cached pipeline, input_state_hash includes pipeline data

**Checkpoint**: Pipeline resolution chain works for all scenarios. Offline mode uses cached Pipeline. Invalid Pipeline falls back gracefully. All US5 tests pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T047 [P] Verify extension case-insensitivity across all tools — `.DNG` and `.dng` treated as same in `extract_tool_config()` and downstream consumers
- [ ] T048 [P] Verify `PipelineToolConfig` extraction is deterministic — same Pipeline always produces same config (sorted sets, stable dict ordering)
- [ ] T049 [P] Verify backward compatibility — run existing analysis tests to confirm Config-based execution unchanged when no Pipeline available
- [ ] T050 Run quickstart.md validation — execute all verification commands from `specs/217-pipeline-driven-tools/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Setup T001-T003 (PipelineToolConfig extraction) only
- **US2 (Phase 3)**: Depends on Setup T001-T003 and US1 T018-T020 (pipeline wiring in run.py)
- **US3 (Phase 4)**: Depends on Setup T004-T012 (Camera entity + discover endpoint + agent client), US2 T022-T024 (Photo_Pairing pipeline integration)
- **US4 (Phase 5)**: Depends on Setup T004-T011 (Camera backend API) — independent of agent-side stories
- **US5 (Phase 6)**: Depends on US1 T020 (pipeline resolution in run.py) — refines and completes the resolution logic
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```text
Setup (Phase 1)
  ├── US1 (Phase 2): PipelineToolConfig → PhotoStats
  │     └── US2 (Phase 3): Pipeline regex → Photo_Pairing
  │           └── US3 (Phase 4): Camera discovery → Photo_Pairing
  │                 └── US5 (Phase 6): Collection pipeline resolution
  ├── US4 (Phase 5): Camera backend → Frontend Resources page (can run parallel to US2/US3)
  └── Polish (Phase 7): after all stories
```

### Parallel Opportunities

- **Phase 1**: T004+T005 (Camera model + Team relationship), T007 (schemas), T009+T010 (API endpoints), T012 (agent client) — all parallelizable
- **Phase 1 tests**: T013, T014, T015, T016, T017 — all parallelizable
- **Phase 5 (US4)**: T029+T030 (contracts + service), T032+T033 (list + dialog components), T040+T041+T042 (component tests) — parallelizable; can start as soon as Phase 1 backend is done, independent of agent work
- **US4 can run in parallel with US2/US3**: Frontend Camera work doesn't depend on agent-side Photo_Pairing changes

---

## Parallel Example: Phase 1 Setup

```bash
# Launch model + schema tasks in parallel:
Task: "Create Camera model in backend/src/models/camera.py"          # T004
Task: "Add cameras relationship to Team in backend/src/models/team.py" # T005
Task: "Create Camera schemas in backend/src/schemas/camera.py"       # T007

# After models complete, launch API endpoints in parallel:
Task: "Create user-facing Camera API in backend/src/api/cameras.py"           # T009
Task: "Create agent-facing discover endpoint in backend/src/api/agent/camera_routes.py" # T010

# Launch all tests in parallel:
Task: "Unit tests for extract_tool_config()"    # T013
Task: "Unit tests for CameraService"            # T014
Task: "Unit tests for Camera API endpoints"     # T015
Task: "Unit tests for discover endpoint"        # T016
Task: "Unit tests for AgentApiClient.discover"  # T017
```

## Parallel Example: US4 Frontend

```bash
# Launch contracts + service in parallel:
Task: "Create Camera TypeScript contracts"  # T029
Task: "Create Camera API service"           # T030

# Launch list + dialog components in parallel:
Task: "Create CameraList component"         # T032
Task: "Create CameraEditDialog component"   # T033
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (PipelineToolConfig + Camera entity)
2. Complete Phase 2: User Story 1 (PhotoStats Pipeline integration)
3. **STOP and VALIDATE**: Run PhotoStats with Pipeline-assigned Collection, verify Pipeline-derived extensions used
4. Deploy/demo if ready — PhotoStats already benefits from Pipeline unification

### Incremental Delivery

1. Setup + US1 → PhotoStats uses Pipeline extensions (MVP)
2. Add US2 → Photo_Pairing uses Pipeline regex and processing names
3. Add US3 → Camera auto-discovery enriches Photo_Pairing reports
4. Add US4 → Frontend Camera management UI (can be done parallel to US2/US3)
5. Add US5 → Collection-specific Pipeline resolution
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (Phase 1) together
2. Once Setup is done:
   - Developer A: US1 → US2 → US3 → US5 (agent-side, sequential chain)
   - Developer B: US4 (frontend Resources page, independent)
3. Stories integrate naturally through shared Camera API

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- `FilenameParser` is NOT modified — retained as fallback
- All Pipeline extraction uses existing `build_pipeline_config()` — no new JSON parsing
- Camera discovery uses DB-agnostic check-before-insert (no `INSERT ON CONFLICT`)
