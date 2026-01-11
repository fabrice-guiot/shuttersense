# Implementation Plan: Calendar of Events

**Branch**: `011-calendar-events` | **Date**: 2026-01-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-calendar-events/spec.md`
**Source**: [GitHub Issue #39](https://github.com/fabrice-guiot/photo-admin/issues/39)

## Summary

Implement a comprehensive Calendar of Events feature for photographers to manage their event schedule. The feature includes:

- **Calendar View**: Monthly calendar displaying events with attendance status colors (Planned=Yellow, Skipped=Red, Attended=Green)
- **Event Management**: Create/edit events with timezone-aware scheduling, multi-day series support, and soft delete
- **Entity Relationships**: Events linked to Categories, Locations (with geocoding), Organizers, and Performers
- **Logistics Tracking**: Ticket, time-off, and travel requirements with status-based color coding
- **TopHeader KPIs**: Event statistics displayed in header following established pattern

This builds on the recently completed timezone support (Issue #56) and follows all GUID conventions (Issue #42).

## Technical Context

**Language/Version**: Python 3.10+ (Backend), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, React 18.3.1, shadcn/ui, Tailwind CSS 4.x
**Storage**: PostgreSQL 12+ with JSONB columns (SQLite for tests)
**Testing**: pytest 8.3+ (backend), vitest 4.0+ (frontend)
**Target Platform**: Web application (modern browsers)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Calendar loads <2s, navigation <1s (per SC-002, SC-003)
**Constraints**: Support 500+ events without degradation (SC-010)
**Scale/Scope**: Single-user photography event management

**New Dependencies** (resolved in research.md):
- **Backend**: `geopy>=2.4.0` (Nominatim geocoding), `timezonefinder>=6.0.0` (offline timezone lookup)
- **Frontend**: Custom CSS Grid calendar extending shadcn/ui Calendar (react-day-picker) - no new major dependencies
- **Timezone data**: Already using native Intl APIs (no additional library needed per Issue #56)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a web feature, not a CLI tool
- [x] **Testing & Quality**: Tests planned using pytest (backend) and vitest (frontend). Target coverage >80% for services
- [x] **User-Centric Design**:
  - For analysis tools: N/A - This is a calendar feature, not an analysis tool
  - Are error messages clear and actionable? Yes - using established API error patterns
  - Is the implementation simple (YAGNI)? Yes - focused on core event management
  - Is structured logging included for observability? Yes - following existing API logging patterns
- [x] **Global Unique Identifiers (GUIDs)**:
  - Events: `evt_` prefix
  - Locations: `loc_` prefix
  - Organizers: `org_` prefix
  - Performers: `prf_` prefix
  - Categories: `cat_` prefix
  - EventSeries: `ser_` prefix
- [x] **Frontend UI Standards**: TopHeader KPI pattern for Events page (FR-043, FR-044, FR-045)
- [x] **Shared Infrastructure**: Using existing database patterns, API structure, and frontend architecture
- [x] **Simplicity**: Following established patterns; no new abstractions except what's required for calendar functionality

**Violations/Exceptions**: None identified. Feature follows all constitution principles.

## Navigation Structure

This feature introduces new sidebar entries and reorganizes existing ones to prevent menu sprawl.

### Proposed Sidebar Structure

```
Dashboard
Collections
Pipelines
Events                    # NEW - Calendar view
Directory                 # NEW - Tabbed page
  ├── Locations (tab)
  ├── Organizers (tab)
  └── Performers (tab)
Analytics                 # Existing - already tabbed
  ├── Trends (tab)
  ├── Reports (tab)
  └── Runs (tab)
Settings                  # NEW section - consolidates config
  ├── Categories (tab)    # NEW - event categories
  ├── Connectors (tab)    # MOVE from top-level
  └── Config (tab)        # MOVE from top-level
```

### Implementation Notes

| Item | Route | Implementation |
|------|-------|----------------|
| Events | `/events` | New page - EventsPage.tsx |
| Directory | `/directory` | New tabbed page - DirectoryPage.tsx |
| Directory/Locations | `/directory?tab=locations` | Tab within DirectoryPage |
| Directory/Organizers | `/directory?tab=organizers` | Tab within DirectoryPage |
| Directory/Performers | `/directory?tab=performers` | Tab within DirectoryPage |
| Settings | `/settings` | New tabbed page - SettingsPage.tsx |
| Settings/Categories | `/settings?tab=categories` | Tab within SettingsPage |
| Settings/Connectors | `/settings?tab=connectors` | MOVE existing ConnectorsPage content |
| Settings/Config | `/settings?tab=config` | MOVE existing ConfigPage content |

### Migration & Backward Compatibility

| Old Route | New Route | Action |
|-----------|-----------|--------|
| `/connectors` | `/settings?tab=connectors` | Redirect (React Router) |
| `/config` | `/settings?tab=config` | Redirect (React Router) |

The existing `ConnectorsPage.tsx` and `ConfigPage.tsx` content will be refactored into `ConnectorsTab.tsx` and `ConfigTab.tsx` components within the Settings page. Old routes will redirect to maintain any bookmarks.

### Future Additions (Out of Scope)

- Cameras, Equipment tabs under Settings

### Tab Pattern

Follow the existing Analytics page pattern using Radix UI Tabs:
```tsx
<Tabs defaultValue="locations">
  <TabsList>
    <TabsTrigger value="locations">Locations</TabsTrigger>
    <TabsTrigger value="organizers">Organizers</TabsTrigger>
    <TabsTrigger value="performers">Performers</TabsTrigger>
  </TabsList>
  <TabsContent value="locations"><LocationsTab /></TabsContent>
  <TabsContent value="organizers"><OrganizersTab /></TabsContent>
  <TabsContent value="performers"><PerformersTab /></TabsContent>
</Tabs>
```

## Project Structure

### Documentation (this feature)

```text
specs/011-calendar-events/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── events-api.yaml  # Event endpoints OpenAPI spec
│   ├── locations-api.yaml
│   ├── organizers-api.yaml
│   ├── performers-api.yaml
│   └── categories-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── event.py           # Event entity with GuidMixin
│   │   ├── event_series.py    # EventSeries for multi-day events
│   │   ├── location.py        # Location entity with geocoding
│   │   ├── organizer.py       # Organizer entity
│   │   ├── performer.py       # Performer entity
│   │   ├── category.py        # Category entity
│   │   └── event_performer.py # Junction table
│   ├── services/
│   │   ├── event_service.py   # Event CRUD and series management
│   │   ├── location_service.py # Location management + geocoding
│   │   ├── organizer_service.py
│   │   ├── performer_service.py
│   │   ├── category_service.py
│   │   └── geocoding_service.py # External geocoding integration
│   ├── api/
│   │   ├── events.py          # Event endpoints
│   │   ├── locations.py       # Location endpoints
│   │   ├── organizers.py      # Organizer endpoints
│   │   ├── performers.py      # Performer endpoints
│   │   └── categories.py      # Category endpoints
│   └── schemas/
│       ├── event.py           # Event Pydantic schemas
│       ├── location.py
│       ├── organizer.py
│       ├── performer.py
│       └── category.py
└── tests/
    └── unit/
        ├── test_event_service.py
        ├── test_location_service.py
        ├── test_geocoding_service.py
        └── test_event_api.py

frontend/
├── src/
│   ├── components/
│   │   ├── events/
│   │   │   ├── EventCalendar.tsx      # Monthly calendar view
│   │   │   ├── EventCard.tsx          # Event display on calendar
│   │   │   ├── EventForm.tsx          # Create/edit form
│   │   │   ├── EventDetails.tsx       # Event detail view/tooltip
│   │   │   ├── LogisticsSection.tsx   # Ticket/travel/time-off tracking
│   │   │   └── SeriesIndicator.tsx    # "x/n" notation display
│   │   ├── directory/
│   │   │   ├── LocationsTab.tsx       # Locations list and management
│   │   │   ├── LocationForm.tsx       # Create/edit location dialog
│   │   │   ├── LocationPicker.tsx     # Address resolution UI
│   │   │   ├── OrganizersTab.tsx      # Organizers list and management
│   │   │   ├── OrganizerForm.tsx      # Create/edit organizer dialog
│   │   │   ├── PerformersTab.tsx      # Performers list and management
│   │   │   └── PerformerForm.tsx      # Create/edit performer dialog
│   │   └── settings/
│   │       ├── CategoriesTab.tsx      # Categories list and management
│   │       ├── ConnectorsTab.tsx      # REFACTOR from ConnectorsPage
│   │       └── ConfigTab.tsx          # REFACTOR from ConfigPage
│   ├── pages/
│   │   ├── EventsPage.tsx             # Calendar page with TopHeader KPIs
│   │   ├── DirectoryPage.tsx          # Tabbed: Locations | Organizers | Performers
│   │   └── SettingsPage.tsx           # Tabbed: Categories (+ future tabs)
│   ├── hooks/
│   │   ├── useEvents.ts               # Events CRUD hook
│   │   ├── useEventStats.ts           # KPI stats hook
│   │   ├── useLocations.ts
│   │   ├── useOrganizers.ts
│   │   └── usePerformers.ts
│   ├── services/
│   │   ├── events.ts                  # Event API service
│   │   ├── locations.ts
│   │   ├── organizers.ts
│   │   └── performers.ts
│   └── contracts/
│       └── api/
│           ├── event-api.ts           # Event TypeScript types
│           ├── location-api.ts
│           ├── organizer-api.ts
│           └── performer-api.ts
└── tests/
    ├── components/
    │   └── EventCalendar.test.tsx
    └── hooks/
        └── useEvents.test.ts
```

**Structure Decision**: Web application structure (Option 2) - extends existing backend/frontend pattern with new entities for events, locations, organizers, performers, and categories.

## Complexity Tracking

> **No Constitution violations identified.** All principles are satisfied by the design.

| Aspect | Assessment |
|--------|------------|
| New Entities | 7 tables (Event, EventSeries, Location, Organizer, Performer, Category, EventPerformer) - justified by spec requirements FR-001 through FR-042 |
| External Service | Nominatim (free, open source) + timezonefinder (offline) - simplest option that meets geocoding requirement FR-032 |
| Calendar UI | Custom CSS Grid extending shadcn/ui Calendar - minimal new dependencies, native Tailwind integration |

## Post-Design Constitution Re-Check

*Verified after Phase 1 design completion.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Independent CLI Tools | N/A | Web feature |
| Testing & Quality | PASS | Test files planned in backend/tests/unit/ and frontend/tests/ |
| User-Centric Design | PASS | TopHeader KPIs, clear error messages, structured logging |
| Global Unique Identifiers | PASS | 6 new prefixes: evt_, ser_, loc_, org_, prf_, cat_ |
| Frontend UI Standards | PASS | useEventStats hook + HeaderStatsContext integration |
| Shared Infrastructure | PASS | GuidMixin, existing API patterns, SQLAlchemy models |
| Simplicity | PASS | No unnecessary abstractions; research selected simplest viable options |

**Design Decisions Summary:**
1. **Geocoding**: Nominatim + timezonefinder (free, privacy-focused, offline timezone)
2. **Calendar UI**: Custom CSS Grid (minimal bundle, native Tailwind/shadcn integration)
3. **Event Series**: Hybrid parent-child pattern (EventSeries + Event tables)

---

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Research | `specs/011-calendar-events/research.md` | Technology decisions with rationale |
| Data Model | `specs/011-calendar-events/data-model.md` | Entity definitions, fields, relationships |
| API Contracts | `specs/011-calendar-events/contracts/` | OpenAPI 3.1 specifications |
| Quickstart | `specs/011-calendar-events/quickstart.md` | Developer reference guide |

**Next Step**: Run `/speckit.tasks` to generate implementation tasks.
