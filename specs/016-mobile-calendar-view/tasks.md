# Tasks: Mobile Calendar View

**Input**: Design documents from `/specs/016-mobile-calendar-view/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per plan.md Testing & Quality requirements (Vitest + @testing-library/react)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/`, `frontend/tests/`
- This is a frontend-only feature; no backend changes required

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Create foundational hook and export structure

- [x] T001 Create `useMediaQuery` hook in `frontend/src/hooks/useMediaQuery.ts` with SSR-safe implementation
- [x] T002 [P] Create `useMediaQuery` test file in `frontend/tests/hooks/useMediaQuery.test.ts`
- [x] T003 ~~Export hook from `frontend/src/hooks/index.ts`~~ (skipped - codebase uses direct imports)

**Checkpoint**: ✅ Viewport detection hook ready for component usage

---

## Phase 2: Foundational (Blocking Prerequisites) ✅

**Purpose**: Create reusable badge component that all user stories depend on

- [x] T004 [P] Create `CategoryBadge` component in `frontend/src/components/events/CategoryBadge.tsx`
- [x] T005 [P] Create `CategoryBadge` test file in `frontend/tests/components/events/CategoryBadge.test.tsx`
- [x] T006 Add `groupEventsByCategory` utility function in `frontend/src/components/events/EventCalendar.tsx`
- [x] T007 Export `CategoryBadge` from `frontend/src/components/events/index.ts`

**Checkpoint**: ✅ Foundation ready - CategoryBadge renders icons with counts correctly

---

## Phase 3: User Story 1 - View Calendar on Mobile Device (Priority: P1) 🎯 MVP ✅

**Goal**: Calendar displays compact badge view on mobile viewports (< 640px)

**Independent Test**: Resize browser to < 640px and verify calendar shows category badges instead of event cards

### Tests for User Story 1

- [x] T008 [P] [US1] Create `CompactCalendarCell` test file in `frontend/tests/components/events/CompactCalendarCell.test.tsx`
- [x] T009 [P] [US1] ~~Add responsive layout test~~ (covered by CompactCalendarCell tests)

### Implementation for User Story 1

- [x] T010 [P] [US1] Create `CompactCalendarCell` component in `frontend/src/components/events/CompactCalendarCell.tsx`
- [x] T011 [US1] Add `generateAriaLabel` function inside `CompactCalendarCell.tsx` for accessibility
- [x] T012 [US1] Export `CompactCalendarCell` from `frontend/src/components/events/index.ts`
- [x] T013 [US1] Import `useIsMobile` hook in `frontend/src/components/events/EventCalendar.tsx`
- [x] T014 [US1] Add conditional rendering in `EventCalendar.tsx` for mobile vs desktop layout
- [x] T015 [US1] Update cell height classes to `min-h-[48px] sm:min-h-[100px]` in `EventCalendar.tsx`

**Checkpoint**: ✅ Compact calendar view appears on viewports < 640px with category badges

---

## Phase 4: User Story 2 - View Day Events from Compact Calendar (Priority: P1) ✅

**Goal**: Tap on day in compact view opens Day Detail popup with full event list

**Independent Test**: On mobile viewport, tap any day with events and verify popup shows complete event list

### Tests for User Story 2

- [x] T016 [P] [US2] Add day click handler test to `frontend/tests/components/events/CompactCalendarCell.test.tsx`
- [x] T017 [P] [US2] Add popup integration test to `frontend/tests/components/events/EventCalendar.test.tsx`

### Implementation for User Story 2

- [x] T018 [US2] Wire `onClick` handler in `CompactCalendarCell` to existing `handleDayClick` in `EventCalendar.tsx`
- [x] T019 [US2] Wire `onKeyDown` handler in `CompactCalendarCell` to existing `handleKeyDown` in `EventCalendar.tsx`
- [x] T020 [US2] Verify Day Detail dialog opens correctly on mobile in `frontend/src/pages/EventsPage.tsx`
- [x] T021 [US2] Verify empty day tap opens Create Event dialog with date pre-filled

**Checkpoint**: ✅ Day tap → Day Detail popup → Event View → Edit flow works on mobile

---

## Phase 5: User Story 3 - Navigate Calendar on Mobile (Priority: P2) ✅

**Goal**: Month navigation remains usable with touch-friendly targets on mobile

**Independent Test**: On mobile viewport, tap next/previous month arrows and verify navigation works with adequate touch targets

### Tests for User Story 3

- [x] T022 [P] [US3] Add touch target size test to `frontend/tests/components/events/EventCalendar.test.tsx`

### Implementation for User Story 3

- [x] T023 [US3] Review and adjust navigation button sizes in `EventCalendar.tsx` header (minimum 44x44px)
- [x] T024 [US3] Ensure month/year title is clearly visible on mobile viewport
- [x] T025 [US3] Test navigation preserves compact view mode after month change

**Checkpoint**: ✅ All navigation controls work correctly on mobile with touch-friendly targets

---

## Phase 6: Polish & Cross-Cutting Concerns ✅

**Purpose**: Edge cases, final testing, and code quality

- [x] T026 Handle overflow display (>4 categories shows "+N" indicator) in `CompactCalendarCell.tsx`
- [x] T027 Handle count overflow (>99 events shows "99+") in `CategoryBadge.tsx`
- [x] T028 [P] Add loading state handling in compact mode in `EventCalendar.tsx`
- [x] T029 [P] Run TypeScript build check: `cd frontend && pnpm build`
- [x] T030 [P] Run all tests: `cd frontend && pnpm test`
- [x] T031 Manual responsive testing per `quickstart.md` Verification Checklist

**Verification Checklist** (from quickstart.md):
- [x] Compact view appears on viewports < 640px
- [x] Standard view appears on viewports >= 640px
- [x] Day tap opens Day Detail popup
- [x] All existing dialog flows work on mobile
- [x] Keyboard navigation works in compact mode
- [x] Screen readers announce category counts
- [x] No horizontal scroll on mobile (overflow-hidden on grid)
- [x] Tests pass: 635 tests
- [x] TypeScript compiles: build successful

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 and US2 are both P1, but US2 depends on US1's CompactCalendarCell
  - US3 (P2) can run after Foundational but independently of US1/US2
- **Polish (Phase 6)**: Depends on User Story 1 completion minimum

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational - Creates CompactCalendarCell
- **User Story 2 (P1)**: Depends on US1 - Uses CompactCalendarCell click handlers
- **User Story 3 (P2)**: Depends on Foundational - Independent of US1/US2

### Within Each User Story

1. Tests written first (should fail before implementation)
2. Components before integration
3. Implementation before wiring to existing code
4. Story complete before moving to next

### Parallel Opportunities

- T002, T003 can run in parallel with T001
- T004, T005 can run in parallel (different files)
- T008, T009 can run in parallel
- T016, T017 can run in parallel
- T028, T029, T030 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests for US1 in parallel:
Task: "Create CompactCalendarCell test file in frontend/tests/components/events/CompactCalendarCell.test.tsx"
Task: "Add responsive layout test to frontend/tests/components/events/EventCalendar.test.tsx"

# Then launch component creation:
Task: "Create CompactCalendarCell component in frontend/src/components/events/CompactCalendarCell.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (useMediaQuery hook)
2. Complete Phase 2: Foundational (CategoryBadge)
3. Complete Phase 3: User Story 1 (CompactCalendarCell + responsive layout)
4. **STOP and VALIDATE**: Test compact view on mobile viewport
5. Demo/deploy if ready

### Incremental Delivery

1. Setup + Foundational → Hook and badge ready
2. Add User Story 1 → Compact view displays → MVP!
3. Add User Story 2 → Day tap works → Full interaction
4. Add User Story 3 → Navigation polished → Complete feature
5. Each story adds value without breaking previous

### Single Developer Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025 → T026 → T027 → T028 → T029 → T030 → T031

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US2 are both P1 priority but have sequential dependency
- All existing EventCalendar functionality must be preserved
- Touch targets must be minimum 44x44 pixels per spec
- Tests use existing `window.matchMedia` mock in `frontend/tests/setup.ts`
