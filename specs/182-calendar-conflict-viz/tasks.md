# Tasks: Calendar Conflict Visualization & Event Picker

**Input**: Design documents from `/specs/182-calendar-conflict-viz/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/conflict-api.yaml, quickstart.md

**Tests**: Included — backend unit tests (test_geo_utils.py, test_conflict_service.py, test_seed_conflict.py), backend integration tests (test_conflict_endpoints.py, test_conflict_config_api.py), and frontend component tests (ConflictBadge, ConflictResolutionPanel, RadarComparisonDialog, ConflictRulesSection, ScoringWeightsSection, DateRangePicker, useDateRange, DimensionMicroBar). Frontend type checking via `npx tsc --noEmit`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- **Backend tests**: `backend/tests/unit/`
- **Migrations**: `backend/migrations/versions/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pure utilities, type definitions, and config registration needed by all stories

- [x] T001 [P] Create haversine distance function in `backend/src/services/geo_utils.py`
  - Pure Python, no dependencies
  - Input: two `(lat, lon)` pairs → output: distance in miles
  - Use `math.radians`, `math.sin`, `math.cos`, `math.asin`, `math.sqrt`
  - Earth radius: 3,958.8 miles

- [x] T002 [P] Create Pydantic schemas in `backend/src/schemas/conflict.py`
  - Match schemas from `contracts/conflict-api.yaml`
  - `ConflictType` enum: `time_overlap`, `distance`, `travel_buffer`
  - `ConflictGroupStatus` enum: `unresolved`, `partially_resolved`, `resolved`
  - `EventScores`, `ScoredEvent`, `ConflictEdge`, `ConflictGroup`, `ConflictSummary`
  - `ConflictDetectionResponse`, `EventScoreResponse`
  - `ConflictDecision`, `ConflictResolveRequest`, `ConflictResolveResponse`
  - `ConflictRulesResponse`, `ConflictRulesUpdateRequest`
  - `ScoringWeightsResponse`, `ScoringWeightsUpdateRequest`

- [x] T003 [P] Create TypeScript types in `frontend/src/contracts/api/conflict-api.ts`
  - Mirror all schema types from `contracts/conflict-api.yaml`
  - `ConflictType`, `ConflictGroupStatus`, `EventScores`, `ScoredEvent`
  - `ConflictEdge`, `ConflictGroup`, `ConflictSummary`, `ConflictDetectionResponse`
  - `EventScoreResponse`, `ConflictDecision`, `ConflictResolveRequest`, `ConflictResolveResponse`
  - `ConflictRulesResponse`, `ConflictRulesUpdateRequest`
  - `ScoringWeightsResponse`, `ScoringWeightsUpdateRequest`

- [x] T004 Register `conflict_rules` and `scoring_weights` in `backend/src/services/config_service.py`
  - Add both strings to `VALID_CATEGORIES` set

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend services, API endpoints, seeding, migration, frontend API client, and tests. MUST be complete before ANY user story can be implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

### Backend Services

- [x] T005 Create ConflictService in `backend/src/services/conflict_service.py`
  - Class `ConflictService(db: Session)` — follows EventService pattern
  - Depends on: `EventService`, `ConfigService`, `geo_utils.haversine_miles()`
  - `get_conflict_rules(team_id)` → reads from ConfigService, returns defaults if missing
  - `get_scoring_weights(team_id)` → reads from ConfigService, returns defaults if missing
  - `score_event(event, weights, performer_ceiling)` → five dimensions + composite (see data-model.md scoring logic)
  - `detect_conflicts(team_id, start_date, end_date)` → returns `ConflictDetectionResponse`
    - Load events via `EventService.list()` with `include_deleted=False`
    - Exclude events where `is_deadline=True`
    - Three detection passes: time overlap, distance, travel buffer (see data-model.md conflict detection logic)
    - Union-Find for connected components → conflict groups
    - Score all events in conflict groups
    - Derive group status from member events' `attendance` values
  - **Extensibility (FR-014)**: Design dimension scoring as a list of `(name, scorer_fn, weight_key)` tuples rather than hardcoded if/else blocks, so new dimensions can be added by appending to the list without restructuring the scoring loop or radar chart axes

- [x] T006 Extend seeding in `backend/src/services/seed_data_service.py`
  - Add `DEFAULT_CONFLICT_RULES` dict (5 entries: distance_threshold_miles, consecutive_window_days, travel_buffer_days, colocation_radius_miles, performer_ceiling)
  - Add `DEFAULT_SCORING_WEIGHTS` dict (5 entries: weight_venue_quality, weight_organizer_reputation, weight_performer_lineup, weight_logistics_ease, weight_readiness)
  - Add `seed_conflict_rules(team_id, user_id)` — follow `seed_collection_ttl()` pattern, does NOT commit
  - Add `seed_scoring_weights(team_id, user_id)` — follow `seed_collection_ttl()` pattern, does NOT commit
  - Update `seed_team_defaults()` to call both new methods
  - Update return tuple to include conflict_rules_created and scoring_weights_created counts

### API Endpoints

- [x] T007 Add conflict detection, scoring, and resolution endpoints to `backend/src/api/events.py`
  - `GET /events/conflicts` → `ConflictService.detect_conflicts()` — requires `start_date` and `end_date` query params
  - `GET /events/{guid}/score` → `ConflictService.score_event()` — returns `EventScoreResponse`
  - `POST /events/conflicts/resolve` → batch-update `attendance` on events from `ConflictResolveRequest`
  - **CRITICAL**: Register `/events/conflicts` and `/events/{guid}/score` routes BEFORE `/{guid}` catch-all
  - All endpoints use `get_tenant_context` for team scoping

- [x] T008 Add conflict_rules and scoring_weights config endpoints to `backend/src/api/config.py`
  - `GET /config/conflict_rules` → read team's conflict rules from ConfigService
  - `PUT /config/conflict_rules` → update team's conflict rules via ConfigService
  - `GET /config/scoring_weights` → read team's scoring weights from ConfigService
  - `PUT /config/scoring_weights` → update team's scoring weights via ConfigService
  - **CRITICAL**: Register before `/{category}` catch-all route

### Migration & Seeding

- [x] T009 Create Alembic migration to seed conflict defaults for existing teams in `backend/migrations/versions/`
  - Follow migration `050` pattern (iterate teams, insert if missing)
  - Use `sa.sql.table()` and `sa.sql.column()` for migration compatibility
  - Seed both `conflict_rules` and `scoring_weights` for all existing teams

### Frontend API Client

- [x] T010 [P] Create API client functions in `frontend/src/services/conflicts.ts`
  - `detectConflicts(startDate, endDate)` → `GET /api/events/conflicts`
  - `getEventScore(guid)` → `GET /api/events/{guid}/score`
  - `resolveConflict(request)` → `POST /api/events/conflicts/resolve`
  - `getConflictRules()` → `GET /api/config/conflict_rules`
  - `updateConflictRules(data)` → `PUT /api/config/conflict_rules`
  - `getScoringWeights()` → `GET /api/config/scoring_weights`
  - `updateScoringWeights(data)` → `PUT /api/config/scoring_weights`
  - Use Axios following existing service patterns

### Tests

- [x] T011 [P] Create haversine tests in `backend/tests/unit/test_geo_utils.py`
  - Known city pairs (e.g., NYC→LA ≈ 2,451 mi, London→Paris ≈ 213 mi)
  - Same point → 0 miles
  - Antipodal points → ~12,450 mi
  - Edge cases: equator, poles

- [x] T012 [P] Create conflict service tests in `backend/tests/unit/test_conflict_service.py`
  - Time overlap: same day overlapping times, all-day vs timed, missing times
  - Distance conflict: events beyond threshold, within threshold, missing coordinates
  - Travel buffer violation: travel events too close in time, co-located events exempt
  - Scoring: all five dimensions with known inputs → expected outputs
  - Composite score: weighted average with custom weights, zero weights
  - Group construction: transitive closure, status derivation
  - Exclude soft-deleted events and deadline events

- [x] T013 [P] Create seeding tests in `backend/tests/unit/test_seed_conflict.py`
  - Idempotency: running twice produces same result
  - All 10 config entries created (5 conflict_rules + 5 scoring_weights)
  - Existing entries not overwritten
  - Does not commit (session check)

- [x] T044 [P] Create conflict endpoint integration tests in `backend/tests/integration/test_conflict_endpoints.py`
  - Follow `test_events_api.py` pattern: use `test_client`, `test_team`, `test_db_session` fixtures
  - **GET /events/conflicts**:
    - Two overlapping events → returns 1 conflict group with `time_overlap` edge
    - Two distant events on consecutive days → returns `distance` conflict
    - Two travel events within buffer → returns `travel_buffer` conflict
    - No conflicts → returns empty `conflict_groups` array
    - Missing `start_date`/`end_date` → 422 validation error
    - Soft-deleted events excluded from results
    - Deadline events (`is_deadline=True`) excluded from results
  - **GET /events/{guid}/score**:
    - Event with known location rating + organizer rating → verify exact dimension scores
    - Event with null location/organizer → verify neutral defaults (50)
    - Non-existent GUID → 404
  - **POST /events/conflicts/resolve**:
    - Confirm one event, skip others → verify attendance updates in DB
    - Invalid event GUID in decisions → 404
    - Verify team scoping (cannot resolve other team's events)

- [x] T045 [P] Create conflict config integration tests in `backend/tests/integration/test_conflict_config_api.py`
  - Follow `test_config_api.py` pattern: use `authenticated_client`, `test_team` fixtures
  - **GET /config/conflict_rules** → returns 5 default values after team seeding
  - **PUT /config/conflict_rules** → partial update (e.g., change only `distance_threshold_miles`), verify only that field changed
  - **GET /config/scoring_weights** → returns 5 default values (20 each)
  - **PUT /config/scoring_weights** → update weights, verify response reflects new values
  - **PUT with invalid values** → negative distance → 422, performer_ceiling=0 → 422
  - Verify team isolation: Team A's config changes don't affect Team B

**Checkpoint**: Foundation ready — all backend services, endpoints, seeding, and tests are in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Detect Scheduling Conflicts on the Calendar (Priority: P1) MVP

**Goal**: Conflict badges appear on calendar cells and event cards when conflicting events are detected.

**Independent Test**: Create overlapping or geographically distant events → verify amber conflict indicators appear on the calendar grid and event cards with descriptive tooltips.

### Implementation for User Story 1

- [ ] T014 [P] [US1] Create useConflicts hook in `frontend/src/hooks/useConflicts.ts`
  - Follow `useEvents()` pattern: `data`, `loading`, `error` state
  - Accepts `startDate` and `endDate` params
  - Calls `detectConflicts()` from conflicts.ts service
  - Returns `ConflictDetectionResponse` data

- [ ] T015 [P] [US1] Create ConflictBadge component in `frontend/src/components/events/ConflictBadge.tsx`
  - Small amber badge with conflict type icon
  - Tooltip on hover: conflict type label + name of conflicting event(s)
  - Use shadcn/ui Tooltip + Lucide icon (e.g., AlertTriangle)
  - Visual states: solid amber (unresolved), dashed gray (resolved)
  - Compact layout on mobile (icon-only, tooltip on tap)

- [ ] T016 [US1] Add conflict indicators to calendar cells in `frontend/src/components/events/EventCalendar.tsx`
  - Integrate `useConflicts` hook for visible date range
  - Map conflict groups to calendar dates
  - Show amber indicator with count of conflict groups per day
  - Resolved groups show dashed gray indicator

- [ ] T017 [US1] Add conflict badge to event cards in `frontend/src/components/events/EventCard.tsx`
  - Check if event GUID appears in any conflict group
  - Render `ConflictBadge` with conflict edge details for tooltip

- [ ] T046 [P] [US1] Create ConflictBadge tests in `frontend/src/components/events/__tests__/ConflictBadge.test.tsx`
  - Follow `AuditTrailPopover.test.tsx` pattern: vitest + React Testing Library
  - Renders amber badge with conflict type icon for unresolved conflict
  - Renders dashed gray badge for resolved conflict
  - Tooltip shows conflict type label and conflicting event name(s)
  - Handles multiple conflict edges (e.g., "Time overlap with Event A, Distance conflict with Event B")

**Checkpoint**: User Story 1 is fully functional. Calendar shows conflict indicators, event cards show badges with tooltips.

---

## Phase 4: User Story 2 — Resolve Conflicts via Quick Actions (Priority: P2)

**Goal**: Users can view conflict details in a day dialog and confirm/skip events to resolve conflicts.

**Independent Test**: Click a conflicted day → view Conflicts tab → confirm one event → verify attendance updates and conflict group becomes resolved.

### Implementation for User Story 2

- [ ] T018 [P] [US2] Create useResolveConflict mutation hook in `frontend/src/hooks/useResolveConflict.ts`
  - Calls `resolveConflict()` from conflicts.ts service
  - Handles loading/error states
  - Triggers refetch of conflict data on success

- [ ] T019 [US2] Create ConflictResolutionPanel in `frontend/src/components/events/ConflictResolutionPanel.tsx`
  - Renders list of conflict group cards
  - Each card shows: conflicting events with composite scores, conflict type label
  - Actions per group: "Confirm" button per event (sets it to planned, others to skipped), "Skip" button (defer)
  - Resolved groups: dimmed/dashed visual treatment
  - Uses `useResolveConflict` hook for mutations
  - Responsive: stack conflict group cards vertically on mobile

- [ ] T020 [US2] Add Conflicts tab to day detail dialog in `frontend/src/pages/EventsPage.tsx`
  - Show "Conflicts" tab alongside existing event list when day has conflicts
  - Tab content renders `ConflictResolutionPanel` with filtered conflict groups for that day
  - Tab badge shows unresolved conflict count

- [ ] T047 [US2] Create ConflictResolutionPanel tests in `frontend/src/components/events/__tests__/ConflictResolutionPanel.test.tsx`
  - Mock `resolveConflict` API via MSW (`server.use()`)
  - Renders conflict group cards with event names and composite scores
  - "Confirm Event A" button sends correct `ConflictResolveRequest` payload (A=planned, B=skipped)
  - "Skip" button does not trigger any API call
  - Resolved groups render with dimmed/dashed visual treatment
  - Group with 3 events: confirming middle event skips both others

**Checkpoint**: User Story 2 is fully functional. Users can resolve conflicts from the day detail dialog.

---

## Phase 5: User Story 3 — Compare Events with Radar Charts (Priority: P3)

**Goal**: Users can compare conflicting events side-by-side with overlaid radar charts and dimension breakdowns.

**Independent Test**: From conflict resolution panel, click "Compare" → verify radar chart renders with correct dimension values, breakdown table matches, confirm action works.

### Implementation for User Story 3

- [ ] T021 [P] [US3] Create useEventScore hook in `frontend/src/hooks/useEventScore.ts`
  - Fetches scores for a single event via `getEventScore()` from conflicts.ts
  - Returns `EventScoreResponse` with loading/error states

- [ ] T022 [US3] Create EventRadarChart in `frontend/src/components/events/EventRadarChart.tsx`
  - Recharts `RadarChart` wrapper for a single event
  - Five axes: Venue Quality, Organizer Reputation, Performer Lineup, Logistics Ease, Readiness
  - Scale 0–100, uses `CHART_COLORS` CSS variables for dark theme compliance
  - Supports overlaying multiple events (distinct colors per polygon)

- [ ] T023 [US3] Create RadarComparisonDialog in `frontend/src/components/events/RadarComparisonDialog.tsx`
  - Dialog (shadcn/ui Dialog or Radix UI) with:
    - Overlaid radar chart (one polygon per event, distinct colors)
    - Dimension breakdown table with exact numerical scores per event
    - Side-by-side event detail summary (location, organizer, performer count, logistics)
  - "Confirm" button per event (triggers same resolve logic as US2)
  - Responsive: chart stacks above table on mobile

- [ ] T024 [US3] Add "Compare" button to ConflictResolutionPanel in `frontend/src/components/events/ConflictResolutionPanel.tsx`
  - Button opens `RadarComparisonDialog` for the selected conflict group
  - Pass conflict group events to the dialog

- [ ] T048 [P] [US3] Create RadarComparisonDialog tests in `frontend/src/components/events/__tests__/RadarComparisonDialog.test.tsx`
  - Dialog renders when open prop is true, hidden when false
  - Displays dimension breakdown table with correct numerical scores
  - Shows side-by-side event details (location, organizer, performer count)
  - "Confirm" button triggers resolve mutation and closes dialog

**Checkpoint**: User Story 3 is fully functional. Users can compare events with radar charts and confirm from the dialog.

---

## Phase 6: User Story 4 — Configure Conflict Rules and Scoring Weights (Priority: P4)

**Goal**: Administrators can customize conflict detection thresholds and scoring dimension weights from Settings.

**Independent Test**: Change distance threshold from 50 to 100 miles → verify events 75 miles apart are no longer flagged.

### Implementation for User Story 4

- [ ] T025 [P] [US4] Create useConflictRules hook in `frontend/src/hooks/useConflictRules.ts`
  - Fetch via `getConflictRules()`, update via `updateConflictRules()`
  - Loading/error/success states
  - Support reset to defaults
  - On successful save: invalidate/refetch conflict data so changes take effect without page refresh (FR-050)

- [ ] T026 [P] [US4] Create useScoringWeights hook in `frontend/src/hooks/useScoringWeights.ts`
  - Fetch via `getScoringWeights()`, update via `updateScoringWeights()`
  - Loading/error/success states
  - Support reset to defaults
  - On successful save: invalidate/refetch scoring data so changes take effect without page refresh (FR-050)

- [ ] T027 [P] [US4] Create ConflictRulesSection in `frontend/src/components/settings/ConflictRulesSection.tsx`
  - Five numeric inputs: distance threshold (miles), consecutive window (days), travel buffer (days), co-location radius (miles), performer ceiling (count)
  - Validation: non-negative integers, performer ceiling ≥ 1
  - "Save" and "Reset Defaults" buttons
  - Uses `useConflictRules` hook

- [ ] T028 [P] [US4] Create ScoringWeightsSection in `frontend/src/components/settings/ScoringWeightsSection.tsx`
  - Five numeric inputs (0–100) with proportional bars showing relative weights
  - Visual bar for each weight showing its proportion of the total
  - Weight of 0 dims the corresponding dimension label
  - "Save" and "Reset Defaults" buttons
  - Uses `useScoringWeights` hook

- [ ] T029 [US4] Add Conflict Rules and Scoring Weights sections to Settings page Configuration tab
  - Locate existing Configuration tab in Settings page
  - Add `ConflictRulesSection` and `ScoringWeightsSection` components
  - Ensure consistent spacing and styling with existing config sections

- [ ] T049 [P] [US4] Create ConflictRulesSection tests in `frontend/src/components/settings/__tests__/ConflictRulesSection.test.tsx`
  - Mock GET/PUT /api/config/conflict_rules via MSW
  - Renders 5 inputs with default values on load
  - Validation: rejects negative values, performer ceiling < 1
  - "Save" sends PUT with updated values
  - "Reset Defaults" restores factory values

- [ ] T050 [P] [US4] Create ScoringWeightsSection tests in `frontend/src/components/settings/__tests__/ScoringWeightsSection.test.tsx`
  - Mock GET/PUT /api/config/scoring_weights via MSW
  - Renders 5 inputs with default values (20 each) on load
  - Proportional bars update when weight values change
  - Weight of 0 dims the corresponding dimension label
  - "Save" sends PUT with updated values

**Checkpoint**: User Story 4 is fully functional. Teams can customize all conflict detection and scoring parameters.

---

## Phase 7: User Story 5 — Unified Date Range Picker for All List Views (Priority: P5)

**Goal**: All non-calendar list views share a date range picker with rolling, calendar-month, and custom range options. Infinite scroll replaces unbounded lists.

**Independent Test**: Select a preset filter (e.g., Needs Tickets) → change range to "Next 60 days" → verify only events within that window appear. Switch to calendar → verify no date range picker shown.

### Implementation for User Story 5

- [ ] T030 [US5] Create useDateRange hook in `frontend/src/hooks/useDateRange.ts`
  - State management for selected range type and computed start/end dates
  - URL sync via `useSearchParams` (persist range selection across navigation)
  - Rolling presets: Next 30 / 60 / 90 days (from today)
  - Calendar-month presets: Next 1 / 2 / 3 / 6 months (1st through end of Nth month)
  - Custom range: explicit start/end dates
  - Default: "Next 30 days"
  - No "All" option

- [ ] T031 [US5] Create DateRangePicker in `frontend/src/components/events/DateRangePicker.tsx`
  - Dropdown/select with preset options grouped: Rolling (30/60/90 days), Monthly (1/2/3/6 months), Custom
  - Custom range: date input fields for start and end dates
  - Uses `useDateRange` hook
  - shadcn/ui Select or Popover pattern
  - Compact layout for inline use above list views
  - Responsive: compact mobile layout (full-width dropdown, stacked custom date inputs)

- [ ] T032 [US5] Modify useEvents hook to accept start_date/end_date parameters
  - Locate existing `useEvents()` hook
  - Add optional `start_date` and `end_date` parameters
  - Pass these to the backend events API as query params
  - Existing preset behavior unchanged when range params not provided

- [ ] T033 [US5] Wire DateRangePicker into all preset list views in `frontend/src/pages/EventsPage.tsx`
  - Show `DateRangePicker` above list when any non-calendar view is active (Upcoming, Needs Tickets, Needs PTO, Needs Travel)
  - Pass selected date range to `useEvents()` hook
  - Hide picker when calendar view is active
  - Restore last-selected range when switching back from calendar to list

- [ ] T034 [US5] Add infinite scroll to event list rendering in `frontend/src/pages/EventsPage.tsx`
  - Replace unbounded list rendering with infinite scroll
  - Load events in pages, append on scroll
  - Bounded by date range (finite result set)
  - Show loading indicator during page fetch
  - Empty state when range returns zero events

- [ ] T051 [P] [US5] Create useDateRange hook tests in `frontend/src/hooks/useDateRange.test.ts`
  - Follow `useRetention.test.ts` pattern: `renderHook()` + `waitFor()`
  - "Next 30 days": start = today, end = today + 30
  - "Next 60 days": start = today, end = today + 60
  - "Next 90 days": start = today, end = today + 90
  - "Next 1 month": start = 1st of current month, end = last day of current month
  - "Next 3 months": start = 1st of current month, end = last day of 3rd month
  - "Next 6 months": start = 1st of current month, end = last day of 6th month
  - Custom range: start and end match user input exactly
  - Default selection is "Next 30 days"
  - URL sync: range persisted to and restored from search params

- [ ] T052 [P] [US5] Create DateRangePicker tests in `frontend/src/components/events/__tests__/DateRangePicker.test.tsx`
  - Renders all preset options (3 rolling + 4 monthly + custom)
  - No "All" option present in dropdown
  - Selecting a preset updates the displayed label
  - Custom mode shows start/end date input fields
  - Empty state: custom range with no dates disables apply

**Checkpoint**: User Story 5 is fully functional. All list views have a consistent date range picker with infinite scroll.

---

## Phase 8: User Story 6 — Plan Ahead with the Timeline Planner (Priority: P6)

**Goal**: A scrollable timeline view with score bars, dimension micro-segments, and conflict connectors for strategic event planning.

**Independent Test**: Switch to Planner view → verify events appear chronologically with score bars, conflict connectors link related events, filters narrow the displayed set.

**Dependencies**: Requires US1 (conflict detection), US3 (radar chart), US5 (date range picker)

### Implementation for User Story 6

- [ ] T035 [P] [US6] Create DimensionMicroBar in `frontend/src/components/events/DimensionMicroBar.tsx`
  - Linearized radar segments: 5 colored segments proportional to dimension scores
  - Each segment uses a distinct color from the design system
  - Hidden on mobile viewports (per FR-045)

- [ ] T036 [US6] Create TimelineEventMarker in `frontend/src/components/events/TimelineEventMarker.tsx`
  - Event row component showing:
    - Composite score bar (filled proportionally to 0–100 score, labeled "Score: X")
    - DimensionMicroBar below the score bar (desktop only)
    - Event name, date, category icon
  - Click to expand inline → show full `EventRadarChart`
  - Mobile: tap opens bottom sheet dialog with radar chart

- [ ] T037 [US6] Create TimelinePlanner in `frontend/src/components/events/TimelinePlanner.tsx`
  - Scrollable chronological timeline grouped by month
  - Renders `TimelineEventMarker` for each event
  - Conflict connectors: vertical amber lines on left margin connecting events in same conflict group, with conflict type label
  - Resolved conflict connectors: dashed gray instead of solid amber
  - Filters: category, conflicts-only, unresolved-only (in addition to date range picker)
  - Click conflict connector → expand overlaid radar comparison
  - Uses `useConflicts` and date range from `useDateRange`

- [ ] T038 [US6] Add Planner view mode to `frontend/src/pages/EventsPage.tsx`
  - Add "Planner" as a new view mode alongside Calendar and preset list views
  - Planner uses `DateRangePicker` from US5 for time window control
  - Wire `TimelinePlanner` component into the view
  - URL-synced view mode selection

- [ ] T053 [P] [US6] Create DimensionMicroBar tests in `frontend/src/components/events/__tests__/DimensionMicroBar.test.tsx`
  - Renders 5 colored segments proportional to dimension scores
  - All scores 0 → renders empty/minimal bar
  - All scores 100 → renders full-width segments
  - Hidden on mobile viewport (via CSS class or media query)

**Checkpoint**: User Story 6 is fully functional. Users can plan ahead using the timeline planner with score visualization.

---

## Phase 9: User Story 7 — View Planner KPIs and Receive Conflict Notifications (Priority: P7)

**Goal**: Header stats for Planner view and notifications when new conflicts are detected.

**Independent Test**: Navigate to Planner → verify KPI badges show correct counts. Create conflicting event → verify notification generated.

**Dependencies**: Requires US1 (conflicts data), US6 (Planner view)

### Implementation for User Story 7

- [ ] T039 [US7] Update header stats for Planner view in `frontend/src/pages/EventsPage.tsx`
  - Set `useHeaderStats()` when Planner view is active
  - KPIs: Conflicts (total groups), Unresolved (count), Events Scored (count), Avg Quality (average composite score)
  - Clear stats on view change or unmount

- [ ] T040 [US7] Add conflict notification via NotificationService in `backend/src/services/notification_service.py` and event hooks
  - Add `"conflict"` to notification categories (alongside existing `job_failure`, `inflection_point`, `agent_status`, `deadline`, `retry_warning`)
  - Add `notify_conflict_detected(self, team_id: int, event_a: Event, event_b: Event, conflict_type: str) -> int` method
    - Follow `notify_job_failure()` pattern: iterate active team users, check preferences, call `send_notification()`
    - Title: "New scheduling conflict detected"
    - Body: "{event_a.title} has a {conflict_type} conflict with {event_b.title} on {event_date}"
    - Data: `{"url": "/events?date={event_date}", "event_guids": [event_a.guid, event_b.guid]}`
  - Add default preference `"conflict": True` to `DEFAULT_PREFERENCES` in NotificationService
  - Hook trigger: In `EventService.create()` and `EventService.update()`, after commit, run conflict detection for the event's date range and notify if new conflicts found
  - Add test in `backend/tests/unit/test_conflict_notification.py` for conflict notification delivery

**Checkpoint**: User Story 7 is complete. Planner shows KPIs and users are notified of new conflicts.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Responsive adaptations, accessibility, and final validation

- [ ] T042 Keyboard navigation for timeline planner
  - Arrow keys to navigate between timeline markers
  - Enter to expand/collapse event details
  - Escape to close expanded views

- [ ] T043 Run quickstart.md validation
  - Execute all test commands from quickstart.md
  - `venv/bin/python -m pytest backend/tests/unit/test_geo_utils.py -v`
  - `venv/bin/python -m pytest backend/tests/unit/test_conflict_service.py -v`
  - `venv/bin/python -m pytest backend/tests/unit/test_seed_conflict.py -v`
  - `venv/bin/python -m pytest backend/tests/integration/test_conflict_endpoints.py -v`
  - `venv/bin/python -m pytest backend/tests/integration/test_conflict_config_api.py -v`
  - `cd frontend && npx tsc --noEmit`
  - `cd frontend && npx vitest run --reporter=verbose`
  - Verify no regressions in existing tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2)
- **US2 (Phase 4)**: Depends on Foundational (Phase 2). Integrates with US1 (conflict indicators update on resolve)
- **US3 (Phase 5)**: Depends on Foundational (Phase 2). Integrates with US2 (Compare button in resolution panel)
- **US4 (Phase 6)**: Depends on Foundational (Phase 2) — independent of US1–US3
- **US5 (Phase 7)**: Depends on Foundational (Phase 2) — independent of US1–US4
- **US6 (Phase 8)**: Depends on US1 (conflict data), US3 (radar chart component), US5 (date range picker)
- **US7 (Phase 9)**: Depends on US1 (conflict data), US6 (Planner view)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS ALL)
    ↓
    ├── US1: Detect Conflicts (P1) ──────────────────────┐
    ├── US2: Resolve Conflicts (P2) ← integrates US1     │
    ├── US3: Radar Charts (P3) ← integrates US2          │
    ├── US4: Settings (P4) ← independent                 │
    └── US5: Date Range Picker (P5) ← independent        │
                                                          ↓
                                              US6: Timeline Planner (P6) ← needs US1, US3, US5
                                                          ↓
                                              US7: KPIs & Notifications (P7) ← needs US1, US6
                                                          ↓
                                              Phase 10: Polish
```

### Within Each User Story

- Hooks before components (data layer before UI)
- Components before page-level integration
- Core implementation before integration points

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 can all run in parallel (different files, no dependencies)
- **Phase 2**: T010, T011, T012, T013, T044, T045 can run in parallel with each other (after T005–T009)
- **US1**: T014, T015, T046 can run in parallel
- **US2**: T047 can run in parallel with T018
- **US3**: T048 can run in parallel with T021
- **US4**: T025, T026, T027, T028, T049, T050 can all run in parallel (different files)
- **US5**: T030 must complete before T031–T034; T051 and T052 can run in parallel with T030
- **US6**: T035 and T053 can run in parallel with other prep work
- **Cross-story**: US4 (Settings) and US5 (Date Range Picker) can run in parallel with US1–US3

---

## Parallel Example: Foundational Phase

```bash
# After T005-T009 complete sequentially, launch parallel tasks:
Task: "Create API client in frontend/src/services/conflicts.ts"          # T010
Task: "Create haversine tests in backend/tests/unit/test_geo_utils.py"   # T011
Task: "Create conflict service tests in backend/tests/unit/test_conflict_service.py"  # T012
Task: "Create seeding tests in backend/tests/unit/test_seed_conflict.py" # T013
Task: "Create conflict endpoint integration tests in backend/tests/integration/test_conflict_endpoints.py"  # T044
Task: "Create conflict config integration tests in backend/tests/integration/test_conflict_config_api.py"  # T045
```

## Parallel Example: User Story 4

```bash
# All US4 hooks, components, and tests target different files:
Task: "Create useConflictRules hook in frontend/src/hooks/useConflictRules.ts"           # T025
Task: "Create useScoringWeights hook in frontend/src/hooks/useScoringWeights.ts"         # T026
Task: "Create ConflictRulesSection in frontend/src/components/settings/ConflictRulesSection.tsx"  # T027
Task: "Create ScoringWeightsSection in frontend/src/components/settings/ScoringWeightsSection.tsx"  # T028
Task: "Create ConflictRulesSection tests in frontend/src/components/settings/__tests__/ConflictRulesSection.test.tsx"  # T049
Task: "Create ScoringWeightsSection tests in frontend/src/components/settings/__tests__/ScoringWeightsSection.test.tsx"  # T050
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 — Detect Conflicts
4. **STOP and VALIDATE**: Conflict indicators visible on calendar and event cards
5. Deploy/demo if ready — delivers core value (scheduling conflict awareness)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Detect Conflicts) → MVP! Conflict awareness on calendar
3. Add US2 (Resolve Conflicts) → Users can act on conflicts
4. Add US3 (Radar Charts) → Data-driven comparison
5. Add US4 (Settings) → Team customization (can be done in parallel with US2/US3)
6. Add US5 (Date Range Picker) → Consistent list view controls (can be done in parallel with US2/US3/US4)
7. Add US6 (Timeline Planner) → Strategic planning view
8. Add US7 (KPIs & Notifications) → Polish
9. Final Polish → Responsive, accessible, validated

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 → US2 → US3 (conflict detection → resolution → comparison chain)
   - Developer B: US4 + US5 (settings + date range picker — independent)
3. After US1+US3+US5 complete: Developer B starts US6 (Timeline Planner)
4. Final: US7 + Polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable (except US6/US7 which have cross-story dependencies)
- **Route ordering gotcha**: `/events/conflicts` MUST be registered before `/events/{guid}` in FastAPI
- **Seeding gotcha**: `seed_conflict_rules()` and `seed_scoring_weights()` must NOT commit — `seed_team_defaults()` commits once at end
- **Soft-deleted events**: Exclude from conflict detection via `include_deleted=False`
- **Deadline entries**: Exclude events where `is_deadline=True` from conflict detection
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
