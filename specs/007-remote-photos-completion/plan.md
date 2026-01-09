# Implementation Plan: Remote Photo Collections Completion

**Branch**: `007-remote-photos-completion` | **Date**: 2026-01-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-remote-photos-completion/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Complete the Remote Photo Collections feature by implementing tool execution (PhotoStats, Photo Pairing, Pipeline Validation) via web interface with real-time progress, result persistence, collection statistics updates for TopHeader KPIs, pipeline management forms, trend visualization, configuration migration, and production polish. Builds on existing FastAPI backend, React/TypeScript frontend, and PostgreSQL database from Phases 1-3.

## Technical Context

**Language/Version**: Python 3.10+ (backend), TypeScript 5.x (frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, WebSocket (starlette)
- Frontend: React 18.3.1, shadcn/ui, Tailwind CSS v4, react-hook-form + Zod, Recharts
**Storage**: PostgreSQL 12+ with JSONB columns (existing connectors, collections tables)
**Testing**:
- Backend: pytest, pytest-cov, pytest-mock, pytest-asyncio (target >80% coverage)
- Frontend: Vitest, React Testing Library, MSW (target >75% coverage)
**Target Platform**: macOS/Linux localhost deployment (single user)
**Project Type**: Web application (backend/ + frontend/ structure)
**Performance Goals**:
- Tool execution within 10% of CLI performance
- 95% WebSocket progress updates within 500ms
- Trend chart rendering < 1 second for 100 data points
**Constraints**:
- Pipeline validation feedback < 2 seconds
- 1000 stored analysis results without performance degradation
- All UI components must use shadcn/ui + Tailwind CSS
**Scale/Scope**: Single user localhost deployment, up to 10,000 files per collection, 1000+ stored results

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: Existing CLI tools (photo_stats.py, photo_pairing.py, pipeline_validation.py) remain standalone. Web interface invokes them programmatically but doesn't create new CLI tools. CLI tools will gain database-first config with YAML fallback.
- [x] **Testing & Quality**: Tests planned with >80% backend and >75% frontend coverage targets. pytest (backend) and Vitest (frontend) are already configured. Coverage requirements explicitly stated in success criteria.
- [x] **User-Centric Design**:
  - HTML report generation included (stored in database, downloadable)
  - Error messages: shadcn/ui Alert components with actionable guidance
  - YAGNI: Form-based pipeline editor (simple), visual graph editor deferred to v2
  - Structured logging: Existing logging_config.py infrastructure
- [x] **Shared Infrastructure**: CLI tools will use PhotoAdminConfig with database extension. Database becomes primary source; YAML remains fallback. Existing config schema preserved.
- [x] **Simplicity**:
  - In-memory job queue (existing JobQueue class) vs external queue system
  - Sequential execution vs parallel workers
  - Form-based pipeline editor vs visual graph editor
- [x] **Frontend UI Standards** (Constitution v1.2.0):
  - All new pages will integrate with TopHeader KPI pattern
  - Stats endpoints defined for each domain (tools, pipelines, config)
  - HeaderStatsContext usage planned for all pages

**Violations/Exceptions**: None. All constitution principles are satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/007-remote-photos-completion/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (existing from Phases 1-3)

backend/
├── src/
│   ├── models/
│   │   ├── collection.py       # Existing - add statistics fields
│   │   ├── connector.py        # Existing
│   │   ├── analysis_result.py  # NEW: Phase 4
│   │   ├── pipeline.py         # NEW: Phase 5
│   │   ├── pipeline_history.py # NEW: Phase 5
│   │   └── configuration.py    # NEW: Phase 7
│   ├── services/
│   │   ├── collection_service.py  # Existing
│   │   ├── connector_service.py   # Existing
│   │   ├── tool_service.py        # NEW: Phase 4
│   │   ├── result_service.py      # NEW: Phase 4
│   │   ├── pipeline_service.py    # NEW: Phase 5
│   │   ├── trend_service.py       # NEW: Phase 6
│   │   └── config_service.py      # NEW: Phase 7
│   ├── api/
│   │   ├── collections.py    # Existing
│   │   ├── connectors.py     # Existing
│   │   ├── tools.py          # NEW: Phase 4
│   │   ├── results.py        # NEW: Phase 4
│   │   ├── pipelines.py      # NEW: Phase 5
│   │   ├── trends.py         # NEW: Phase 6
│   │   └── config.py         # NEW: Phase 7
│   ├── db/
│   │   └── migrations/versions/
│   │       ├── 001_initial_collections.py  # Existing
│   │       ├── 002_add_collection_stats.py # Existing
│   │       ├── 003_analysis_results.py     # NEW: Phase 4
│   │       ├── 004_pipelines.py            # NEW: Phase 5
│   │       └── 005_configurations.py       # NEW: Phase 7
│   └── utils/
│       ├── job_queue.py    # Existing - in-memory job queue
│       └── websocket.py    # NEW: Phase 4 - progress broadcasting
└── tests/
    ├── unit/
    └── integration/

frontend/
├── src/
│   ├── components/
│   │   ├── tools/          # NEW: Phase 4
│   │   │   ├── ToolSelector.tsx
│   │   │   ├── ProgressMonitor.tsx
│   │   │   └── ResultViewer.tsx
│   │   ├── results/        # NEW: Phase 4
│   │   │   ├── ResultList.tsx
│   │   │   └── ReportViewer.tsx
│   │   ├── pipelines/      # NEW: Phase 5
│   │   │   ├── PipelineList.tsx
│   │   │   ├── PipelineFormEditor.tsx
│   │   │   ├── NodeEditor.tsx
│   │   │   └── FilenamePreview.tsx
│   │   ├── trends/         # NEW: Phase 6
│   │   │   ├── TrendChart.tsx
│   │   │   ├── DateRangeFilter.tsx
│   │   │   └── CollectionCompare.tsx
│   │   └── config/         # NEW: Phase 7
│   │       ├── ConfigEditor.tsx
│   │       ├── ConflictResolver.tsx
│   │       └── ImportDialog.tsx
│   ├── pages/
│   │   ├── CollectionsPage.tsx  # Existing
│   │   ├── ConnectorsPage.tsx   # Existing
│   │   ├── ToolsPage.tsx        # NEW: Phase 4
│   │   ├── ResultsPage.tsx      # NEW: Phase 4
│   │   ├── PipelinesPage.tsx    # NEW: Phase 5
│   │   └── ConfigPage.tsx       # NEW: Phase 7
│   ├── hooks/
│   │   ├── useTools.ts          # NEW: Phase 4
│   │   ├── useResults.ts        # NEW: Phase 4
│   │   ├── usePipelines.ts      # NEW: Phase 5
│   │   ├── useTrends.ts         # NEW: Phase 6
│   │   └── useConfig.ts         # NEW: Phase 7
│   └── services/
│       ├── tools.ts             # NEW: Phase 4
│       ├── results.ts           # NEW: Phase 4
│       ├── pipelines.ts         # NEW: Phase 5
│       ├── trends.ts            # NEW: Phase 6
│       └── config.ts            # NEW: Phase 7
└── tests/
    ├── hooks/
    └── components/

# CLI Tools (repository root - existing, enhanced in Phase 7)
photo_stats.py           # Existing - add database config support
photo_pairing.py         # Existing - add database config support
pipeline_validation.py   # Existing - add database config support
utils/
└── config_manager.py    # Existing - extend for database config
```

**Structure Decision**: Web application structure (Option 2) selected. Existing backend/ and frontend/ directories from Phases 1-3 are extended with new models, services, API routes, components, and pages. CLI tools at repository root receive database configuration support.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
