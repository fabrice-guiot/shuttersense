# Research: Calendar Conflict Visualization & Event Picker

**Feature Branch**: `182-calendar-conflict-viz`
**Created**: 2026-02-13

## R1: Configuration Storage Pattern

**Decision**: Reuse the existing `configurations` table with two new categories: `conflict_rules` and `scoring_weights`.

**Rationale**: The `configurations` table already stores team-scoped key-value pairs with JSONB values, audit columns, and a unique constraint on `(team_id, category, key)`. This is the exact pattern used by `event_statuses` and `collection_ttl`. No schema migration needed for the table itself — only a data migration to seed defaults for existing teams.

**Alternatives considered**:
- New dedicated tables (`conflict_rules`, `scoring_weights`): Rejected — adds schema complexity with no benefit over the existing flexible config system.
- In-memory defaults only (no persistence): Rejected — teams need to customize values, and those customizations must persist.

**Implementation detail**: Add `"conflict_rules"` and `"scoring_weights"` to `VALID_CATEGORIES` in `config_service.py`. Follow the seeding pattern from `seed_event_statuses()` and `seed_collection_ttl()`.

---

## R2: Conflict Detection Service Design

**Decision**: Create a new `ConflictService` class in `backend/src/services/conflict_service.py` that computes conflicts at query time from event data.

**Rationale**: Computing conflicts on-demand avoids stale data (events change frequently), eliminates the need for background jobs or triggers, and keeps the data model simple. The O(n^2) pair-comparison is acceptable for the expected scale (hundreds of events per team per quarter).

**Alternatives considered**:
- Persisted conflict table with triggers: Rejected — adds complexity, stale data risk, and trigger maintenance burden.
- Background job for conflict detection: Rejected — violates YAGNI (on-demand is sufficient for v1) and would require agent involvement per Constitution Principle VI.

**Implementation detail**: `ConflictService` loads events via `EventService.list()` (which already supports date range filtering and team_id scoping), then runs three detection passes (time overlap, distance, travel buffer), builds a union-find structure for conflict groups, and scores each event in parallel.

---

## R3: Haversine Distance Calculation

**Decision**: Implement haversine formula as pure Python in `backend/src/services/geo_utils.py` (~10 lines).

**Rationale**: The haversine formula is simple, well-understood, and sufficient for great-circle distance. The existing `Location` model already has `latitude` (Numeric(10,7)) and `longitude` (Numeric(10,7)) fields. No external geo library is needed.

**Alternatives considered**:
- `geopy` library: Rejected — adds a dependency for a trivial calculation.
- PostGIS extension: Rejected — overkill for point-to-point distance; not all deployments support PostGIS.

---

## R4: Event Scoring Dimensions

**Decision**: Five dimensions scored on a 0–100 scale using existing model fields.

| Dimension | Source | Scoring Logic |
|-----------|--------|---------------|
| Venue Quality | `location.rating` (1–5, nullable) | `rating * 20`. Null → 50 (neutral). |
| Organizer Reputation | `organizer.rating` (1–5, nullable) | `rating * 20`. Null → 50 (neutral). |
| Performer Lineup | `EventPerformer` count where `status = 'confirmed'` | `min(count / ceiling, 1.0) * 100`. Ceiling from config (default: 5). |
| Logistics Ease | `travel_required`, `timeoff_required`, `ticket_required` | Each `False`/`None` → +33.3. All false = 100. All true = 0. |
| Readiness | `ticket_status`, `timeoff_status`, `travel_status` | Each resolved status (ready/approved/booked) → +33.3 of its share. Fully ready = 100. |

**Rationale**: These five dimensions cover the key decision factors identified in the PRD. All data comes from existing model fields — no new data collection required. The 0–100 normalization enables consistent radar chart display.

**Alternatives considered**:
- Fewer dimensions (just score + conflict type): Rejected — loses the multi-dimensional comparison value that drives the radar chart UX.
- More dimensions (historical PhotoStats scores): Deferred to follow-up as noted in PRD open questions.

---

## R5: Conflict Group Resolution Model

**Decision**: Conflict groups are identified by an ephemeral `group_id` (e.g., `cg_1`, `cg_2`) computed at query time. Resolution is achieved by updating `attendance` on individual events — not by persisting conflict group state.

**Rationale**: Since conflict groups are computed from event data, their resolution status is derived from the attendance values of their member events. A group is "resolved" when at most one event has `attendance = 'planned'` or `attendance = 'attended'`. This means resolution is just an event update — no new entities or state machines needed.

**Alternatives considered**:
- Persisted conflict groups with explicit status: Rejected — groups are unstable (they change when events change) and would require synchronization logic.

**Implementation detail**: The `POST /api/events/conflicts/resolve` endpoint accepts a list of `{event_guid, attendance}` decisions and batch-updates the events. The frontend tracks group_id for display purposes only.

---

## R6: Frontend Radar Chart Integration

**Decision**: Use Recharts `RadarChart` component (already in project dependencies at v2.15.0).

**Rationale**: Recharts is already a project dependency. The RadarChart component supports multiple overlaid polygons (one per event), PolarGrid, PolarAngleAxis, and interactive tooltips — all required by the comparison dialog.

**Alternatives considered**:
- D3.js custom radar: Rejected — unnecessary complexity when Recharts provides the component out of the box.
- Chart.js radar: Rejected — would add a dependency; Recharts is already available.

**Implementation detail**: Chart colors use existing `CHART_COLORS` from design system CSS variables (`--chart-1` through `--chart-5`) for dark theme compliance.

---

## R7: Unified Date Range Picker & Timeline Planner Architecture

**Decision**: Introduce a shared date range picker component used by all non-calendar list views (preset filters and Planner). The calendar view is unchanged (forced 1-month window with month scroll). The Planner is a new view mode on EventsPage alongside the existing Calendar and preset views.

**Rationale**: The EventsPage currently has two view modes: Calendar (month grid, 42 days) and preset list views (Upcoming, Needs Tickets, Needs PTO, Needs Travel). The preset views have no user-controllable time window — "Upcoming" is hardcoded to 30 days, and the "needs" views return all matching events regardless of date. Adding a Planner with its own range picker while leaving the presets unbounded creates an asymmetry. A unified date range picker solves this by giving all list-based views the same time-windowing control.

**Date range options**:
- Rolling windows: Next 30 days, Next 60 days, Next 90 days (from today, not calendar-aligned)
- Calendar-month windows: Next 1 / 2 / 3 / 6 months (1st of current month through end of Nth month)
- Custom range: User picks explicit start and end dates
- No "All" option — every list view must be bounded

**List rendering**: Infinite scroll within the date-range-bounded result set (no classic pagination). The date range naturally limits the result set size.

**Default range**: "Next 30 days" — matching the existing Upcoming preset behavior.

**Alternatives considered**:
- Planner-only range picker (leave presets unchanged): Rejected — creates inconsistent UX across list views on the same page.
- Separate page (`/events/planner`): Rejected — violates the established pattern on EventsPage.
- "All" option: Rejected — unbounded queries are a performance risk and offer no meaningful user value over a 6-month window.

---

## R8: Seeding and Migration Strategy

**Decision**: Extend `SeedDataService` with two new methods (`seed_conflict_rules`, `seed_scoring_weights`) called from `seed_team_defaults()`. Create one Alembic data migration to seed defaults for existing teams.

**Rationale**: Follows the exact pattern used for `seed_event_statuses()` and `seed_collection_ttl()`. The `seed_team_defaults()` method is called by both `seed_first_team.py` and `POST /api/admin/teams`, so all team creation paths are covered.

**Implementation detail**:
- New methods do NOT commit (caller `seed_team_defaults()` commits once at end).
- Return tuple extended: `(categories_created, event_statuses_created, ttl_configs_created, conflict_rules_created, scoring_weights_created)`.
- Migration follows pattern from migrations `019`, `043`, `050`: iterate existing teams, check for existing configs, insert defaults.

---

## R9: Logistics Scoring — Handling Nullable Fields

**Decision**: For Logistics Ease and Readiness dimensions, treat `None`/null as "not required" (positive for Logistics Ease) or "not applicable" (neutral for Readiness).

**Rationale**: Events inherit logistics flags from their series, organizer, or location. A `None` value for `travel_required` means "not specified" — the conservative interpretation is that travel is not required (contributing positively to Logistics Ease). For Readiness, if a logistics dimension is not required, its status is irrelevant — only required items count toward the Readiness score.

**Scoring detail**:
- **Logistics Ease**: Count `False` or `None` values among `[travel_required, timeoff_required, ticket_required]`. Each contributes ~33.3 points.
- **Readiness**: For each required item (`True`), check if its status is resolved (`ticket_status='ready'`, `timeoff_status='approved'`, `travel_status='booked'`). Score = (resolved / required) * 100. If nothing is required, Readiness = 100.
