# Tasks: User Timezone Display

**Input**: Design documents from `/specs/010-user-timezone-display/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included - NFR-004 requires 90%+ test coverage for the date formatting utility.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/`, `frontend/tests/`
- Testing framework: Vitest with jsdom

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the centralized date formatting utility file and export structure

- [x] T001 Create date formatting utility file at `frontend/src/utils/dateFormat.ts` with empty module structure and JSDoc header
- [x] T002 Update `frontend/src/utils/index.ts` to export date formatting functions (formatDateTime, formatRelativeTime, formatDate, formatTime)
- [x] T003 Create test file at `frontend/tests/utils/dateFormat.test.ts` with test suite structure and Vitest imports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core date parsing and Intl API support detection that ALL formatting functions depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement `parseDate()` helper function in `frontend/src/utils/dateFormat.ts` - parses ISO 8601 strings to Date objects, handles null/undefined/invalid inputs
- [x] T005 [P] Implement `hasIntlSupport()` detection function in `frontend/src/utils/dateFormat.ts` - checks for Intl.DateTimeFormat availability
- [x] T006 [P] Implement `hasRelativeTimeSupport()` detection function in `frontend/src/utils/dateFormat.ts` - checks for Intl.RelativeTimeFormat availability
- [x] T007 Write unit tests for parseDate() in `frontend/tests/utils/dateFormat.test.ts` - valid ISO strings, null, undefined, empty string, invalid strings

**Checkpoint**: Foundation ready - date parsing and API detection working. User story implementation can now begin.

---

## Phase 3: User Story 1 - View Timestamps in Local Timezone (Priority: P1) 🎯 MVP

**Goal**: Display all timestamps in user's local timezone with human-readable format (e.g., "Jan 7, 2026, 3:45 PM")

**Independent Test**: View any page with timestamps (Connectors list, Collections page) and verify times display in local timezone with medium date and short time format.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US1] Write unit tests for `formatDateTime()` in `frontend/tests/utils/dateFormat.test.ts` - valid dates, custom options, fallback behavior
- [x] T009 [P] [US1] Write unit tests for `formatDate()` in `frontend/tests/utils/dateFormat.test.ts` - date-only formatting with various dateStyle options
- [x] T010 [P] [US1] Write unit tests for `formatTime()` in `frontend/tests/utils/dateFormat.test.ts` - time-only formatting with various timeStyle options

### Implementation for User Story 1

- [x] T011 [US1] Implement `formatDateTime()` function in `frontend/src/utils/dateFormat.ts` - uses Intl.DateTimeFormat with dateStyle: 'medium', timeStyle: 'short' default
- [x] T012 [US1] Implement `formatDate()` function in `frontend/src/utils/dateFormat.ts` - date-only formatting with configurable dateStyle
- [x] T013 [US1] Implement `formatTime()` function in `frontend/src/utils/dateFormat.ts` - time-only formatting with configurable timeStyle
- [x] T014 [US1] Run US1 tests to verify all pass

### Component Migration for User Story 1

- [x] T015 [P] [US1] Migrate `frontend/src/components/connectors/ConnectorList.tsx` - replace inline formatDate() with imported formatDateTime()
- [x] T016 [P] [US1] Migrate `frontend/src/components/results/ResultsTable.tsx` - replace inline formatDate() with imported formatDateTime()
- [x] T017 [P] [US1] Migrate `frontend/src/components/results/ResultDetailPanel.tsx` - replace inline formatDate() with imported formatDateTime()
- [x] T018 [P] [US1] Migrate `frontend/src/components/pipelines/PipelineCard.tsx` - replace inline formatting with imported formatDate()
- [x] T019 [P] [US1] Migrate `frontend/src/components/tools/JobProgressCard.tsx` - replace inline formatDate() with imported formatDateTime()
- [x] T020 [P] [US1] Migrate `frontend/src/components/trends/TrendChart.tsx` - replace inline formatting with imported formatDate()
- [x] T021 [P] [US1] Migrate `frontend/src/components/trends/TrendSummaryCard.tsx` - replace inline formatting with imported formatDate()
- [x] T022 [P] [US1] Migrate `frontend/src/components/trends/PipelineValidationTrend.tsx` - replace inline formatting with imported formatDateTime()

**Checkpoint**: All timestamps display in local timezone with consistent formatting. User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - View Relative Time for Recent Events (Priority: P1)

**Goal**: Display recent timestamps as relative times (e.g., "2 hours ago", "yesterday") for improved UX

**Independent Test**: Create or update an item and verify the timestamp shows as "just now" or "X minutes ago" rather than an absolute date.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [P] [US2] Write unit tests for `getRelativeTimeUnit()` helper in `frontend/tests/utils/dateFormat.test.ts` - seconds, minutes, hours, days, weeks, months, years calculation
- [ ] T024 [P] [US2] Write unit tests for `formatRelativeTime()` in `frontend/tests/utils/dateFormat.test.ts` - recent times (seconds to days), threshold behavior (7+ days returns absolute)

### Implementation for User Story 2

- [ ] T025 [US2] Implement `getRelativeTimeUnit()` helper in `frontend/src/utils/dateFormat.ts` - calculates appropriate time unit (seconds, minutes, hours, days, etc.) from millisecond difference
- [ ] T026 [US2] Implement `formatRelativeTime()` function in `frontend/src/utils/dateFormat.ts` - uses Intl.RelativeTimeFormat with numeric: 'auto', falls back to absolute for dates older than 7 days
- [ ] T027 [US2] Run US2 tests to verify all pass

### Component Updates for User Story 2 (Optional Relative Time Usage)

- [ ] T028 [US2] Document relative time usage guidelines - add comment in `frontend/src/utils/dateFormat.ts` explaining when to use formatRelativeTime vs formatDateTime

**Checkpoint**: Relative time formatting works for recent events. User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Graceful Handling of Missing Dates (Priority: P2)

**Goal**: Display "Never" for null/undefined dates and "Invalid date" for malformed values

**Independent Test**: View a connector that has never been validated and confirm "Never" displays instead of a blank or error.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T029 [P] [US3] Write unit tests for null/undefined handling in `frontend/tests/utils/dateFormat.test.ts` - formatDateTime(null), formatDateTime(undefined), formatDateTime('')
- [ ] T030 [P] [US3] Write unit tests for invalid date handling in `frontend/tests/utils/dateFormat.test.ts` - formatDateTime('invalid'), formatDateTime('2026-13-45')

### Implementation for User Story 3

- [ ] T031 [US3] Add null/undefined handling to `formatDateTime()` in `frontend/src/utils/dateFormat.ts` - return "Never" for falsy values
- [ ] T032 [US3] Add invalid date handling to `formatDateTime()` in `frontend/src/utils/dateFormat.ts` - return "Invalid date" when Date.getTime() is NaN
- [ ] T033 [US3] Add null/undefined/invalid handling to `formatRelativeTime()` in `frontend/src/utils/dateFormat.ts` - consistent with formatDateTime
- [ ] T034 [US3] Add null/undefined/invalid handling to `formatDate()` and `formatTime()` in `frontend/src/utils/dateFormat.ts`
- [ ] T035 [US3] Run US3 tests to verify all pass

**Checkpoint**: All user stories are now independently functional. Null dates show "Never", invalid dates show "Invalid date".

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T036 [P] Add JSDoc documentation to all exported functions in `frontend/src/utils/dateFormat.ts`
- [ ] T037 [P] Write locale variation tests in `frontend/tests/utils/dateFormat.test.ts` - verify formatting works with mocked locales (en-US, fr-FR, de-DE)
- [ ] T038 [P] Write edge case tests in `frontend/tests/utils/dateFormat.test.ts` - year boundaries, DST transitions
- [ ] T039 Run full test suite and verify 90%+ coverage for `frontend/src/utils/dateFormat.ts`
- [ ] T040 Remove all remaining inline formatDate() helper functions from migrated components (verify none remain)
- [ ] T041 Run `npm run lint` in frontend directory and fix any linting errors
- [ ] T042 Run `npm run build` in frontend directory and verify no build errors
- [ ] T043 Manual verification: Test application in browser, verify timestamps display correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 priority and can proceed in parallel
  - US3 (P2) can proceed in parallel or after US1/US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on US1, independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on US1/US2, independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks follow test tasks
- Component migrations can run in parallel (different files)
- Story complete checkpoint before moving to next priority

### Parallel Opportunities

**Within Phase 2 (Foundational):**
- T005 and T006 can run in parallel (different functions)

**Within Phase 3 (User Story 1):**
- T008, T009, T010 can run in parallel (different test suites)
- T015 through T022 can ALL run in parallel (8 different component files)

**Within Phase 4 (User Story 2):**
- T023 and T024 can run in parallel (different test suites)

**Within Phase 5 (User Story 3):**
- T029 and T030 can run in parallel (different test cases)

**Within Phase 6 (Polish):**
- T036, T037, T038 can run in parallel (different concerns)

**Across Phases (after Foundational):**
- US1, US2, US3 phases can all proceed in parallel if team capacity allows

---

## Parallel Example: User Story 1 Component Migration

```bash
# Launch all 8 component migrations in parallel:
Task: "Migrate frontend/src/components/connectors/ConnectorList.tsx"
Task: "Migrate frontend/src/components/results/ResultsTable.tsx"
Task: "Migrate frontend/src/components/results/ResultDetailPanel.tsx"
Task: "Migrate frontend/src/components/pipelines/PipelineCard.tsx"
Task: "Migrate frontend/src/components/tools/JobProgressCard.tsx"
Task: "Migrate frontend/src/components/trends/TrendChart.tsx"
Task: "Migrate frontend/src/components/trends/TrendSummaryCard.tsx"
Task: "Migrate frontend/src/components/trends/PipelineValidationTrend.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T022)
4. **STOP and VALIDATE**: Test timestamps display correctly in local timezone
5. Deploy/demo if ready - this alone provides significant value

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP: Local timezone display
3. Add User Story 2 → Test independently → Enhancement: Relative times
4. Add User Story 3 → Test independently → Polish: Null handling
5. Complete Polish phase → Production ready

### Parallel Team Strategy

With multiple developers:

1. All complete Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core formatting + component migration)
   - Developer B: User Story 2 (relative time formatting)
   - Developer C: User Story 3 (null/invalid handling)
3. Stories complete and integrate independently
4. All reconvene for Polish phase

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests are REQUIRED per NFR-004 (90%+ coverage target)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- 8 components to migrate - all can be migrated in parallel after formatDateTime() is implemented
