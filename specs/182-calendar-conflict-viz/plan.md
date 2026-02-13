# Implementation Plan: Calendar Conflict Visualization & Event Picker

**Branch**: `182-calendar-conflict-viz` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/182-calendar-conflict-viz/spec.md`

## Summary

Add conflict detection, multi-dimensional event scoring, and a timeline planner to the Events page. The backend introduces a new `ConflictService` that detects three conflict types (time overlap, distance, travel buffer) and scores events across five quality dimensions with configurable weights. Two new configuration categories (`conflict_rules`, `scoring_weights`) are stored in the existing `configurations` table. The frontend adds conflict indicators on the calendar, a conflict resolution panel, radar chart comparison dialogs, and a new Timeline Planner tab. No new database tables are needed — conflicts are computed at query time.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2 (backend); React 18.3.1, Recharts 2.15.0, shadcn/ui, Radix UI (frontend)
**Storage**: PostgreSQL (existing `configurations` table for new settings — no new tables or migrations for schema changes)
**Testing**: pytest with SQLite test fixtures (backend); `npx tsc --noEmit` for type checking (frontend)
**Target Platform**: Web application (browser, responsive desktop + mobile)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: Conflict detection for up to ~500 events per team per date range in <1s; radar chart rendering at 60fps
**Constraints**: Conflict detection is O(n^2) — acceptable for expected cardinality (hundreds of events per team per quarter)
**Scale/Scope**: Hundreds of events per team per quarter; 5 scoring dimensions; 10 new config entries per team

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Agent-Only Tool Execution (Principle I)**: Not applicable — this feature is web-only (no analysis tool execution, no agent changes).
- [x] **Testing & Quality (Principle II)**: Tests planned at three levels: (1) Backend unit tests for `conflict_service.py` (all 3 conflict types, scoring logic, composite calculation), `geo_utils.py` (haversine accuracy), and seeding (idempotency). (2) Backend integration tests for all 7 new API endpoints (conflict detection, scoring, resolution, config CRUD) following existing `test_events_api.py` / `test_config_api.py` patterns. (3) Frontend component tests for key UI components (ConflictBadge, ConflictResolutionPanel, DateRangePicker, useDateRange hook) following existing vitest + React Testing Library patterns. Frontend type checking via `npx tsc --noEmit`.
- [x] **User-Centric Design (Principle III)**:
  - Not an analysis tool — no HTML reports needed.
  - Error messages: Validation errors for invalid config values; clear tooltips for conflict types.
  - Simplicity: No new tables, computed conflicts avoid stale data, existing config system reused.
  - Logging: Conflict detection will log query parameters and result counts.
- [x] **Global Unique Identifiers (Principle IV)**: Events use existing `evt_` GUIDs. Conflict group IDs are ephemeral identifiers (e.g., `cg_1`) generated at query time, not persisted — they do not require GuidMixin.
- [x] **Multi-Tenancy (Principle V)**: All new endpoints use `get_tenant_context`. ConflictService filters events by `team_id`. Config entries are team-scoped via existing `configurations` table pattern.
- [x] **Agent-Only Execution (Principle VI)**: Not applicable — no job processing in this feature.
- [x] **Audit Trail (Principle VII)**: Configuration entries inherit audit columns from the existing `Configuration` model (which uses `AuditMixin`). No new entities are created.
- [x] **TopHeader KPI (Frontend Standard)**: Planner tab will set header stats (Conflicts, Unresolved, Events Scored, Avg Quality) via `useHeaderStats()` context.
- [x] **Single Title Pattern (Frontend Standard)**: Events page title stays in TopHeader. Planner is a tab — no new `<h1>` elements.
- [x] **Simplicity (Philosophy)**: Reuses existing config system, computes conflicts at query time (no persistence), haversine is ~10 lines of pure Python, all scoring uses existing model fields.

**Violations/Exceptions**: None. All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/182-calendar-conflict-viz/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── conflict-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── services/
│   │   ├── conflict_service.py       # NEW — Conflict detection + event scoring
│   │   ├── geo_utils.py              # NEW — Haversine distance calculation
│   │   └── seed_data_service.py      # MODIFIED — Add seed_conflict_rules(), seed_scoring_weights()
│   ├── api/
│   │   ├── events.py                 # MODIFIED — Add conflict/score/resolve endpoints
│   │   └── config.py                 # MODIFIED — Register new config categories
│   └── schemas/
│       └── conflict.py               # NEW — Conflict group, edge, score schemas
├── tests/
│   └── unit/
│       ├── test_conflict_service.py  # NEW — Conflict detection + scoring tests
│       ├── test_geo_utils.py         # NEW — Haversine distance tests
│       └── test_seed_conflict.py     # NEW — Seeding idempotency tests
└── migrations/
    └── versions/
        └── XXX_seed_conflict_defaults.py  # NEW — Seed defaults for existing teams

frontend/
├── src/
│   ├── components/
│   │   ├── events/
│   │   │   ├── DateRangePicker.tsx            # NEW — Unified date range picker (shared by all list views)
│   │   │   ├── ConflictBadge.tsx              # NEW — Amber warning badge
│   │   │   ├── ConflictResolutionPanel.tsx    # NEW — Conflict group cards + quick-resolve
│   │   │   ├── RadarComparisonDialog.tsx      # NEW — Side-by-side radar comparison dialog
│   │   │   ├── EventRadarChart.tsx            # NEW — Single-event Recharts RadarChart
│   │   │   ├── TimelinePlanner.tsx            # NEW — Scrollable timeline view
│   │   │   ├── TimelineEventMarker.tsx        # NEW — Individual event row in timeline
│   │   │   └── DimensionMicroBar.tsx          # NEW — Linearized radar micro-bar
│   │   └── settings/
│   │       ├── ConflictRulesSection.tsx       # NEW — Conflict rules config form
│   │       └── ScoringWeightsSection.tsx      # NEW — Scoring weights config form
│   ├── contracts/api/
│   │   └── conflict-api.ts                    # NEW — Conflict/score TypeScript types
│   ├── hooks/
│   │   ├── useConflicts.ts                    # NEW — Fetch conflict groups for date range
│   │   ├── useDateRange.ts                    # NEW — Date range state + URL sync for list views
│   │   ├── useEventScore.ts                   # NEW — Fetch scores for single event
│   │   ├── useConflictRules.ts                # NEW — CRUD for conflict rules config
│   │   ├── useScoringWeights.ts               # NEW — CRUD for scoring weights config
│   │   └── useResolveConflict.ts              # NEW — Mutation hook for resolving conflicts
│   ├── services/
│   │   └── conflicts.ts                       # NEW — Conflict/score API client functions
│   └── pages/
│       └── EventsPage.tsx                     # MODIFIED — Add Planner view, date range picker, conflict integration
└── (no new test files — TypeScript type checking via tsc)
```

**Structure Decision**: Web application (Option 2). All new backend code follows existing patterns in `backend/src/services/` and `backend/src/api/`. All new frontend components go under `frontend/src/components/events/` and `frontend/src/components/settings/`. No new directories needed beyond `contracts/` in the specs folder.

## Complexity Tracking

> No violations. All principles satisfied — no entries needed.
