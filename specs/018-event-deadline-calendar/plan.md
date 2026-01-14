# Implementation Plan: Event Deadline Calendar Display

**Branch**: `018-event-deadline-calendar` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-event-deadline-calendar/spec.md`

## Summary

Display Event Series deadlines as distinct "virtual" events in the calendar view. When an Event Series has a deadline_date set, a deadline entry automatically appears in the calendar showing "[Deadline] Event Series Name" with red styling and ClockAlert icon. Deadline entries are protected from direct modification - all changes flow through the parent Event Series. Primary use case is tracking post-event image processing deadlines (client delivery, competition submissions).

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, React 18.3.1, shadcn/ui, Tailwind CSS 4.x, Lucide React icons
**Storage**: PostgreSQL 12+ with JSONB columns (SQLite for tests)
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Web application (Linux server backend, modern browsers frontend)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Deadline entry synchronization < 1 second, calendar rendering unchanged
**Constraints**: No breaking changes to existing Events API consumers
**Scale/Scope**: Feature affects Event Series entities and calendar display only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a web application feature, not a CLI tool
- [x] **Testing & Quality**: Tests planned for both backend (pytest) and frontend (Vitest). Coverage will include:
  - EventSeries deadline field CRUD operations
  - Deadline entry automatic synchronization
  - API protection for deadline entries
  - Frontend calendar display of deadlines
- [x] **User-Centric Design**:
  - For analysis tools: N/A - Not an analysis tool
  - Are error messages clear and actionable? Yes - clear rejection messages when attempting to modify deadline entries
  - Is the implementation simple (YAGNI)? Yes - storing deadline entries as Events with is_deadline marker
  - Is structured logging included for observability? Yes - will log deadline sync operations
- [x] **Global Unique Identifiers (GUIDs)**:
  - Deadline entries will use existing Event GUID pattern (`evt_` prefix)
  - EventSeries already uses `ser_` prefix
  - API responses will use `.guid` property only
- [x] **Frontend UI Standards**:
  - Single Title Pattern: Deadline entries will use existing EventCard display
  - TopHeader KPI: Event stats endpoint already exists
- [x] **Shared Infrastructure**: Uses existing PhotoAdminConfig and config schema
- [x] **Simplicity**: Deadline entries stored as regular Event records with `is_deadline=True` marker - no new tables required

**Violations/Exceptions**: None - feature follows all constitution principles.

**Post-Design Re-evaluation** (after Phase 1): All checks still pass. Design artifacts confirm:
- Tests outlined in quickstart.md and research.md
- Clear error messages defined in contracts (403 with series_guid for navigation)
- Simple Event-based storage with boolean flag (no new tables)
- GUID pattern followed for deadline entries (`evt_` prefix)

## Project Structure

### Documentation (this feature)

```text
specs/018-event-deadline-calendar/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── event.py           # Add is_deadline field
│   │   └── event_series.py    # Add deadline_date, deadline_time fields
│   ├── services/
│   │   └── event_service.py   # Add deadline sync logic
│   ├── api/
│   │   └── events.py          # Add protection for deadline entries
│   └── schemas/
│       ├── event.py           # Add is_deadline to responses
│       └── event_series.py    # Add deadline fields to requests/responses
└── tests/
    ├── unit/
    │   └── test_event_service_deadline.py
    └── integration/
        └── test_events_api_deadline.py

frontend/
├── src/
│   ├── components/events/
│   │   ├── EventCard.tsx      # Add deadline styling
│   │   └── EventCalendar.tsx  # Display deadline entries
│   ├── contracts/api/
│   │   └── event-api.ts       # Add deadline fields to types
│   └── hooks/
│       └── useEvents.ts       # No changes needed
└── tests/
    └── components/events/
        └── EventCard.test.tsx  # Add deadline display tests
```

**Structure Decision**: Web application structure with backend/ and frontend/ directories. Feature extends existing Event and EventSeries models - no new tables or components required.

## Complexity Tracking

> No constitution violations. Feature uses simple approach of storing deadline entries as Event records with a type marker.

| Consideration | Decision | Rationale |
|---------------|----------|-----------|
| Deadline storage | Event record with `is_deadline=True` | Reuses existing Event infrastructure, appears automatically in Events API |
| Synchronization | Service-layer logic | Simple, testable, no database triggers needed |
| Protection | API validation | Clean separation, clear error messages |
