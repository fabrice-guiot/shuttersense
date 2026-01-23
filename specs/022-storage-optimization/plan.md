# Implementation Plan: Storage Optimization for Analysis Results

**Branch**: `022-storage-optimization` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-storage-optimization/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement storage optimization for analysis results that reduces storage consumption by 80%+ for stable collections through Input State tracking, no-change detection, and automatic retention-based cleanup. The feature adds team-level retention configuration, Input State hash computation (SHA-256), and intelligent deduplication where unchanged collections reference previous results instead of storing duplicates.

## Technical Context

**Language/Version**: Python 3.10+ (Backend/Agent), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, React 18.3.1, shadcn/ui, Tailwind CSS 4.x
**Storage**: PostgreSQL 12+ with JSONB columns
**Testing**: pytest (backend), vitest (frontend - if applicable)
**Target Platform**: Linux server (backend), Modern browsers (frontend), macOS/Windows/Linux (agent)
**Project Type**: web (backend + frontend + agent)
**Performance Goals**: <50ms overhead for no-change detection, <1s file list hash for 10K files
**Constraints**: 80% storage reduction for stable collections, NO_CHANGE results <1KB
**Scale/Scope**: Teams with 10K+ results, collections with 100K+ files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a web application feature, not a CLI tool
- [x] **Testing & Quality**: Tests planned for all new services, models, and API endpoints. pytest configured.
- [x] **User-Centric Design**:
  - N/A for analysis tools: This enhances existing result storage, not a new analysis tool
  - Error messages: Clear messages for deleted source reports, retention configuration validation
  - Simplicity (YAGNI): Single-level reference following, no complex chaining
  - Structured logging: All cleanup and optimization operations logged
- [x] **Shared Infrastructure**: Uses existing Configuration model pattern for team-level settings
- [x] **Simplicity**: Direct hash comparison, batch deletion, no complex deduplication algorithms
- [x] **Global Unique Identifiers**: New fields use GUIDs (`download_report_from` stores GUID)
- [x] **Multi-Tenancy**: All retention settings and cleanup scoped to team_id
- [x] **Agent-Only Execution**: Input State computation happens on agent; server stores results

**Violations/Exceptions**: None

## Project Structure

### Documentation (this feature)

```text
specs/022-storage-optimization/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── __init__.py           # Add NO_CHANGE to ResultStatus enum
│   │   ├── analysis_result.py    # Add input_state_hash, input_state_json, no_change_copy, download_report_from
│   │   └── storage_metrics.py    # NEW: StorageMetrics model for cumulative cleanup stats
│   ├── schemas/
│   │   ├── results.py            # Update response schemas with new fields
│   │   ├── jobs.py               # Add previous_result to job claim response
│   │   ├── retention.py          # NEW: Retention configuration schemas
│   │   └── storage_metrics.py    # NEW: Storage metrics response schemas
│   ├── services/
│   │   ├── result_service.py     # Add get_report with reference following
│   │   ├── job_service.py        # Add previous_result lookup, NO_CHANGE completion handling
│   │   ├── job_coordinator_service.py  # Add NO_CHANGE completion, increment metrics
│   │   ├── cleanup_service.py    # NEW: Retention-based cleanup service (updates StorageMetrics)
│   │   ├── input_state.py        # NEW: Input State hash computation
│   │   └── storage_metrics_service.py  # NEW: Storage metrics service
│   └── api/
│       ├── results.py            # Update report download endpoint
│       ├── analytics.py          # NEW: GET /api/analytics/storage endpoint
│       └── agent/routes.py       # Update job claim with previous_result, add NO_CHANGE completion
└── tests/
    ├── unit/
    │   ├── test_input_state.py       # NEW: Input State hash tests
    │   ├── test_cleanup_service.py   # NEW: Cleanup service tests
    │   └── test_storage_metrics_service.py  # NEW: Storage metrics service tests
    └── integration/
        ├── test_no_change_flow.py    # NEW: End-to-end no-change detection
        └── test_retention_cleanup.py # NEW: Retention cleanup integration

frontend/
├── src/
│   ├── components/
│   │   ├── settings/
│   │   │   └── ResultRetentionSection.tsx  # NEW: Retention config UI
│   │   └── analytics/
│   │       └── ReportStorageTab.tsx  # NEW: Storage metrics dashboard
│   ├── pages/
│   │   └── AnalyticsPage.tsx     # Add "Report Storage" tab
│   ├── contracts/
│   │   └── api/
│   │       └── retention-api.ts    # NEW: Retention API types
│   └── hooks/
│       └── useRetention.ts         # NEW: Retention config hooks
└── tests/
    └── components/
        └── ResultRetentionSection.test.tsx  # NEW: Component tests

agent/
├── src/
│   └── input_state.py       # NEW: Input State computation
└── tests/
    └── unit/
        └── test_input_state.py  # NEW: Input State tests
```

**Structure Decision**: Web application structure (backend + frontend + agent). This feature touches all three components: backend stores and manages results, frontend displays configuration, agent computes Input State hashes.

## Complexity Tracking

> No constitution violations requiring justification.
