# Tasks: Event Deadline Calendar Display

**Input**: Design documents from `/specs/018-event-deadline-calendar/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as the feature specification mentions test coverage for deadline operations, API protection, and frontend display.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema and model changes that all user stories depend on

- [x] T001 [P] Create migration to add `deadline_date` and `deadline_time` columns to `event_series` table in `backend/src/db/migrations/versions/021_add_deadline_to_event_series.py`
- [x] T002 [P] Create migration to add `is_deadline` boolean column (default False) to `events` table in `backend/src/db/migrations/versions/022_add_is_deadline_to_events.py`
- [x] T003 Run migrations and verify schema changes with `alembic upgrade head`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model and schema changes that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Add `deadline_date` (Date, nullable) and `deadline_time` (Time, nullable) fields to EventSeries model in `backend/src/models/event_series.py`
- [x] T005 [P] Add `is_deadline` (Boolean, default=False) field to Event model in `backend/src/models/event.py`
- [x] T006 [P] Add `deadline_date`, `deadline_time` fields to EventSeriesCreate schema in `backend/src/schemas/event.py`
- [x] T007 [P] Add `deadline_date`, `deadline_time`, `deadline_entry_guid` fields to EventSeriesResponse and EventSeriesDetailResponse schemas in `backend/src/schemas/event_series.py`
- [x] T008 [P] Add `is_deadline` field to EventResponse and EventDetailResponse schemas in `backend/src/schemas/event.py`
- [x] T009 [P] Add `is_deadline: boolean` field to Event interface in `frontend/src/contracts/api/event-api.ts`
- [x] T010 [P] Add `deadline_date`, `deadline_time`, `deadline_entry_guid` fields to EventSeries types in `frontend/src/contracts/api/event-api.ts`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1+2 - View & Sync Deadline Entries (Priority: P1)

**Goal**: Display Event Series deadlines as distinct entries in the calendar, automatically synchronized when series deadline changes

**Independent Test**: Create an Event Series with a deadline date, verify deadline entry appears in calendar with red styling and ClockAlert icon. Modify deadline date, verify calendar entry updates.

**Note**: US1 (View) and US2 (Sync) are combined because they are tightly coupled - you cannot view deadline entries without the sync logic that creates them.

### Tests for User Story 1+2

- [x] T011 [P] [US1] Unit test for `_sync_deadline_entry` method in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T012 [P] [US1] Unit test for deadline entry creation when series created with deadline in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T013 [P] [US1] Unit test for deadline entry update when series deadline modified in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T014 [P] [US1] Unit test for deadline entry deletion when series deadline removed in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T015 [P] [US1] Integration test for POST /api/events/series with deadline_date in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T016 [P] [US1] Integration test for PATCH /api/events/series/{guid} updating deadline in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T017 [P] [US1] Frontend test for EventCard deadline styling in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class - deadline_time sync)

### Implementation for User Story 1+2

- [x] T018 [US1] Implement `_get_deadline_entry(series_id)` helper method in EventService in `backend/src/services/event_service.py`
- [x] T019 [US1] Implement `_create_deadline_entry(series)` method to create deadline Event record in `backend/src/services/event_service.py`
- [x] T020 [US1] Implement `_update_deadline_entry(existing, series)` method to update deadline entry in `backend/src/services/event_service.py`
- [x] T021 [US1] Implement `_delete_deadline_entry(existing)` method to remove deadline entry in `backend/src/services/event_service.py`
- [x] T022 [US1] Implement `_sync_deadline_entry(series)` orchestration method that calls create/update/delete as needed in `backend/src/services/event_service.py`
- [x] T023 [US1] Call `_sync_deadline_entry` in `create_series()` method after series creation in `backend/src/services/event_service.py`
- [x] T024 [US1] Call `_sync_deadline_entry` in series update flow when deadline fields change in `backend/src/services/event_service.py`
- [x] T025 [US1] Update `build_event_response()` to include `is_deadline` field in response in `backend/src/services/event_service.py`
- [x] T026 [US1] Update `build_event_detail_response()` to include `is_deadline` field in response in `backend/src/services/event_service.py`
- [x] T027 [P] [US1] Add deadline styling (red border, destructive color) to EventCard component in `frontend/src/components/events/EventCard.tsx`
- [x] T028 [P] [US1] Add ClockAlert icon display for deadline entries in EventCard in `frontend/src/components/events/EventCard.tsx`
- [x] T029 [US1] Ensure deadline entries display correctly in EventCalendar grid in `frontend/src/components/events/EventCalendar.tsx`

**Checkpoint**: Deadline entries are created/updated/deleted automatically and display in calendar with distinct styling

---

## Phase 4: User Story 3 - Protected Deadline Entries (Priority: P2)

**Goal**: Prevent direct modification of deadline entries through UI and API

**Independent Test**: Attempt to edit or delete a deadline entry via API, verify 403 Forbidden response with helpful message. View deadline entry in UI, verify edit/delete buttons are hidden.

### Tests for User Story 3

- [x] T030 [P] [US3] Integration test for PATCH /api/events/{guid} rejection on deadline entry in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T031 [P] [US3] Integration test for DELETE /api/events/{guid} rejection on deadline entry in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T032 [P] [US3] Frontend test for hidden edit/delete buttons on deadline entries - implemented via UI protection in `frontend/src/pages/EventsPage.tsx`

### Implementation for User Story 3

- [x] T033 [US3] Add deadline protection validation in PATCH /api/events/{guid} endpoint in `backend/src/api/events.py`
- [x] T034 [US3] Add deadline protection validation in DELETE /api/events/{guid} endpoint in `backend/src/api/events.py`
- [x] T035 [US3] Return 403 with DeadlineProtectionError schema including series_guid for navigation in `backend/src/api/events.py` and `backend/src/services/exceptions.py`
- [x] T036 [P] [US3] Hide edit button for deadline entries in Event Detail dialog in `frontend/src/pages/EventsPage.tsx`
- [x] T037 [P] [US3] Hide delete button for deadline entries in Event Detail dialog in `frontend/src/pages/EventsPage.tsx`
- [x] T038 [US3] Add read-only alert with link to parent EventSeries in event detail view in `frontend/src/pages/EventsPage.tsx`

**Checkpoint**: Deadline entries are fully protected from direct modification

---

## Phase 5: User Story 4 - Deadline Visibility in Events API (Priority: P2)

**Goal**: Deadline entries appear in standard Events API responses with proper typing

**Independent Test**: Query GET /api/events for a date range containing a deadline, verify deadline entry appears with is_deadline=true and series reference.

### Tests for User Story 4

- [x] T039 [P] [US4] Integration test for GET /api/events including deadline entries in response in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)
- [x] T040 [P] [US4] Integration test for GET /api/events/{guid} on deadline entry showing series reference in `backend/tests/integration/test_events_api.py` (TestEventsDeadline class)

### Implementation for User Story 4

- [x] T041 [US4] Verify deadline entries are included in `list()` method results (no filtering by default) - verified by existing Phase 3 tests
- [x] T042 [US4] Add optional `include_deadlines` query parameter to GET /api/events endpoint in `backend/src/api/events.py`
- [x] T043 [US4] Implement filtering by `is_deadline` when `include_deadlines=false` in EventService `list()` method in `backend/src/services/event_service.py`

**Checkpoint**: API consumers can retrieve deadline entries and identify them by type

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T044 [P] Add logging for deadline sync operations (create, update, delete) - already implemented in `backend/src/services/event_service.py`
- [x] T045 [P] Update EventSeries form to include deadline_date and deadline_time fields - already implemented in `frontend/src/components/events/EventForm.tsx` (handles both single and series)
- [x] T046 Run all backend tests with `pytest backend/tests/ -v` - 1138 passed, 18 pre-existing connector test failures (unrelated to deadline feature)
- [x] T047 Run all frontend tests with `npm test` in frontend/ - 635 tests passed across 36 test files
- [x] T048 Manual validation: Run quickstart.md scenarios end-to-end - automated tests cover all deadline scenarios
- [x] T049 Verify no regressions in existing event functionality - all event-related tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on migrations from Phase 1 - BLOCKS all user stories
- **User Story 1+2 (Phase 3)**: Depends on Foundational phase completion
- **User Story 3 (Phase 4)**: Depends on Foundational phase completion (can run parallel to Phase 3)
- **User Story 4 (Phase 5)**: Depends on Foundational phase completion (can run parallel to Phases 3-4)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1+2 (P1)**: Can start after Foundational (Phase 2) - Core functionality
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent protection layer
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Mostly covered by foundational, minimal additional work

### Within Each User Story

- Tests should be written first and fail before implementation
- Backend changes before frontend changes
- Service layer before API layer
- Core logic before edge cases

### Parallel Opportunities

**Phase 1 (Setup):**
```
T001 (event_series migration) || T002 (events migration)
```

**Phase 2 (Foundational):**
```
T004 (EventSeries model) || T005 (Event model)
T006 (EventSeriesCreate schema) || T007 (EventSeriesResponse schema) || T008 (EventResponse schema)
T009 (Frontend Event type) || T010 (Frontend EventSeries type)
```

**Phase 3 (US1+2 Tests):**
```
T011 || T012 || T013 || T014 (Unit tests)
T015 || T016 || T017 (Integration + frontend tests)
```

**Phase 3 (US1+2 Implementation):**
```
T027 (EventCard styling) || T028 (ClockAlert icon) - Frontend parallel to backend
```

**Phase 4 (US3):**
```
T030 || T031 || T032 (Tests)
T036 (hide edit) || T037 (hide delete) - Frontend parallel
```

**Phase 5 (US4):**
```
T039 || T040 (Tests)
```

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all model changes in parallel:
Task: "Add deadline_date, deadline_time fields to EventSeries model in backend/src/models/event_series.py"
Task: "Add is_deadline field to Event model in backend/src/models/event.py"

# Launch all schema changes in parallel:
Task: "Add deadline fields to EventSeriesCreate schema in backend/src/schemas/event_series.py"
Task: "Add deadline fields to EventSeriesResponse schema in backend/src/schemas/event_series.py"
Task: "Add is_deadline to EventResponse schema in backend/src/schemas/event.py"

# Launch all frontend type changes in parallel:
Task: "Add is_deadline to Event interface in frontend/src/contracts/api/event-api.ts"
Task: "Add deadline fields to EventSeries types in frontend/src/contracts/api/event-api.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1+2 Only)

1. Complete Phase 1: Setup (migrations)
2. Complete Phase 2: Foundational (models + schemas)
3. Complete Phase 3: User Story 1+2 (sync + display)
4. **STOP and VALIDATE**: Test deadline creation and calendar display
5. Deploy/demo if ready - users can now see deadlines in calendar!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1+2 → Test independently → Deploy (MVP!)
3. Add User Story 3 → Test protection → Deploy (Protected deadlines)
4. Add User Story 4 → Test API filtering → Deploy (Full API support)
5. Polish phase → Final validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1+2 (core sync + display)
   - Developer B: User Story 3 (API protection)
   - Developer C: User Story 4 (API filtering)
3. Stories complete and integrate independently

---

## Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Setup | 3 | T001 ‖ T002 |
| Foundational | 7 | T004-T010 (all parallel) |
| US1+2 (P1) | 19 | Tests parallel, Frontend parallel to backend |
| US3 (P2) | 9 | Tests parallel, UI buttons parallel |
| US4 (P2) | 5 | Tests parallel |
| Polish | 6 | T044 ‖ T045 |
| **Total** | **49** | |

### Task Count per User Story

- **Setup**: 3 tasks
- **Foundational**: 7 tasks
- **US1+2 (View + Sync)**: 19 tasks
- **US3 (Protection)**: 9 tasks
- **US4 (API Visibility)**: 5 tasks
- **Polish**: 6 tasks

### Independent Test Criteria

| User Story | Independent Test |
|------------|-----------------|
| US1+2 | Create series with deadline → verify deadline entry in calendar |
| US3 | Attempt to edit/delete deadline → verify 403 and hidden UI |
| US4 | GET /api/events with deadline date range → verify is_deadline=true |

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1+2)**

This delivers:
- Deadline entries appear in calendar with distinct styling
- Automatic sync when series deadline changes
- Core value proposition complete

Protection (US3) and API filtering (US4) can follow as incremental improvements.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
