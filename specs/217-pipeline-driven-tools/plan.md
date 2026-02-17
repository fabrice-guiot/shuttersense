# Implementation Plan: Pipeline-Driven Analysis Tools

**Branch**: `217-pipeline-driven-tools` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/217-pipeline-driven-tools/spec.md`

## Summary

Migrate PhotoStats and Photo_Pairing from Config-based to Pipeline-based configuration, aligning all three analysis tools on a single source of truth: the Pipeline assigned to (or defaulting for) the target Collection. Introduce a Camera entity for auto-discovery during analysis, and consolidate Camera + Pipeline management under a new "Resources" page.

**Technical approach**: Extract a `PipelineToolConfig` dataclass from Pipeline nodes/edges using the existing `build_pipeline_config()` infrastructure. Wire this into the agent's `_execute_tool()` flow with graceful fallback to `TeamConfigCache` when no Pipeline is available. Add a `Camera` model with agent-facing discovery endpoint and user-facing CRUD API. Refactor `PipelinesPage` into a tab within a new `ResourcesPage`.

## Technical Context

**Language/Version**: Python 3.11+ (agent and backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); Click, httpx (agent); React 18.3.1, shadcn/ui, Tailwind CSS 4.x, Lucide React (frontend)
**Storage**: PostgreSQL 12+ (production), SQLite (tests) — new `cameras` table with `(team_id, camera_id)` unique constraint
**Testing**: pytest (backend/agent), Vitest (frontend)
**Target Platform**: Linux server (backend), cross-platform (agent binary), browser (frontend)
**Project Type**: Web application (backend + frontend + agent)
**Performance Goals**: PipelineToolConfig extraction <10ms for 100 nodes; Camera discover batch <200ms for 50 IDs; <5% analysis overhead vs Config-based
**Constraints**: DB-agnostic patterns (no PostgreSQL-specific SQL — tests run on SQLite); offline-capable agent; backward-compatible with existing TeamConfigCache format
**Scale/Scope**: 3 components (agent, backend, frontend), ~15 new files, ~25 modified files, 1 new DB migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Agent-Only Tool Execution (I)**: Tools execute through `shuttersense-agent run`. No standalone scripts added. New `PipelineToolConfig` extraction lives in `agent/src/analysis/`. Offline mode supported with cached Pipeline data.
- [x] **Testing & Quality (II)**: Tests planned for all layers — `extract_tool_config()` unit tests, Camera service CRUD/discover tests, API endpoint tests, frontend hook/component tests. pytest (backend/agent) and Vitest (frontend).
- [x] **User-Centric Design (III)**: Existing HTML report generation unchanged. Camera names and processing method names enhance report readability. Clear fallback warnings when Pipeline unavailable. Structured logging for Pipeline extraction and Camera discovery.
- [x] **Global Unique Identifiers (IV)**: Camera entity uses `GuidMixin` with prefix `cam_`. All API endpoints use GUIDs. Frontend contracts include `guid` field.
- [x] **Multi-Tenancy (V)**: Camera scoped by `team_id`. All endpoints use `TenantContext`. Cross-team access returns 404. Agent discovery uses `agent.team_id`.
- [x] **Agent-Only Execution (VI)**: Camera discovery happens during agent analysis execution. Server provides discovery endpoint but never executes tools. Pipeline resolution occurs in agent run flow.
- [x] **Audit Trail (VII)**: Camera model uses `AuditMixin`. All API response schemas include `audit: Optional[AuditInfo]`. Frontend Camera list includes "Modified" column with `AuditTrailPopover`. Camera service sets `created_by_user_id`/`updated_by_user_id`.
- [x] **Single Title Pattern**: Resources page uses `pageTitle: 'Resources'` in route config. No `<h1>` in page content. Tab content has no `<h2>` titles. `pageHelp` provides description via tooltip.
- [x] **TopHeader KPI Display**: Camera stats and Pipeline stats switch per-tab via `useHeaderStats().setStats()`. Each tab manages its own stats and clears on unmount.
- [x] **Shared Infrastructure**: `PhotoAdminConfig` / `TeamConfigCache` retained as fallback. Config-based parameters preserved for no-Pipeline Collections. `FilenameParser` unchanged.
- [x] **Simplicity**: `PipelineToolConfig` is a simple dataclass extraction — no new abstractions or frameworks. Camera auto-discovery uses check-before-insert (no ORM magic). Resources page follows existing `DirectoryPage` tab pattern exactly.

**Violations/Exceptions**: None. All constitution principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/217-pipeline-driven-tools/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── camera-api.yaml  # Camera REST API contract
│   └── agent-api.yaml   # Agent-facing Camera discovery contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
agent/
├── src/
│   ├── analysis/
│   │   └── pipeline_tool_config.py     # NEW: PipelineToolConfig extraction
│   ├── api_client.py                   # MODIFIED: add discover_cameras()
│   └── cache/
│       └── __init__.py                 # MODIFIED: TeamConfigCache pipeline fields
├── cli/
│   └── run.py                          # MODIFIED: pipeline resolution, tool wiring
└── tests/
    └── unit/
        ├── test_pipeline_tool_config.py # NEW: extraction tests
        └── test_camera_discovery.py     # NEW: agent-side discovery tests

backend/
├── src/
│   ├── models/
│   │   ├── camera.py                   # NEW: Camera model
│   │   └── team.py                     # MODIFIED: add cameras relationship
│   ├── services/
│   │   └── camera_service.py           # NEW: CRUD + discover
│   ├── schemas/
│   │   └── camera.py                   # NEW: Pydantic schemas
│   └── api/
│       ├── cameras.py                  # NEW: user-facing Camera endpoints
│       └── agent/
│           └── camera_routes.py        # NEW: agent-facing discover endpoint
├── alembic/versions/
│   └── xxx_add_cameras_table.py        # NEW: migration
└── tests/unit/
    ├── test_camera_service.py          # NEW: service tests
    └── test_camera_api.py              # NEW: endpoint tests

frontend/src/
├── pages/
│   └── ResourcesPage.tsx               # NEW: tabbed Resources page
├── components/
│   ├── cameras/
│   │   ├── CamerasTab.tsx              # NEW: Camera list tab
│   │   ├── CameraList.tsx              # NEW: Camera table
│   │   └── CameraEditDialog.tsx        # NEW: edit/confirm dialog
│   └── pipelines/
│       └── PipelinesTab.tsx            # NEW: refactored from PipelinesPage
├── contracts/api/
│   └── camera-api.ts                   # NEW: TypeScript contracts
├── hooks/
│   └── useCameras.ts                   # NEW: Camera data hooks
├── services/
│   └── cameras.ts                      # NEW: Camera API service
└── hooks/__tests__/
    └── useCameras.test.tsx             # NEW: hook tests
```

**Structure Decision**: Web application (Option 2) — changes span agent, backend, and frontend. Follows existing directory conventions exactly.

## Complexity Tracking

> No violations found. All constitution principles satisfied without exceptions.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
