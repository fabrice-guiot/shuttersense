# Tasks: Dark Theme Compliance

**Input**: Design documents from `/specs/009-dark-theme-compliance/`
**Prerequisites**: plan.md (required), spec.md (required), research.md
**Branch**: `009-dark-theme-compliance`
**Related Issue**: [GitHub Issue #55](https://github.com/fabrice-guiot/photo-admin/issues/55)

**Tests**: Unit tests included for new ErrorBoundary component. Other verification is via visual inspection and Lighthouse audits as per spec.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/` for source code
- **Tests**: `frontend/tests/` for test files
- **Docs**: `frontend/docs/` for design system documentation

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure and prepare for changes

- [X] T001 Audit current design tokens in `frontend/src/globals.css` to confirm all needed tokens exist
- [X] T002 [P] Run grep search for hardcoded colors in `frontend/src/components/` to establish baseline of violations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add design tokens and global styles that all user stories depend on

**⚠️ CRITICAL**: Scrollbar and base token work must complete before story-specific implementations

- [X] T003 Add scrollbar design tokens to `:root` in `frontend/src/globals.css` (--scrollbar-thumb, --scrollbar-track)
- [X] T004 Add success/info color tokens to `:root` in `frontend/src/globals.css` if not already present (--success, --success-foreground, --info, --info-foreground)
- [X] T005 Create error components directory structure at `frontend/src/components/error/`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Scrollbar Visual Consistency (Priority: P1) 🎯 MVP

**Goal**: Style all scrollbars with dark theme colors using CSS custom properties for cross-browser support

**Independent Test**: Open any page with scrollable content and verify scrollbars use dark theme styling (dark track, muted thumb, brighter on hover)

### Implementation for User Story 1

- [X] T006 [US1] Add Firefox scrollbar styles (scrollbar-color, scrollbar-width) to `frontend/src/globals.css`
- [X] T007 [US1] Add WebKit scrollbar pseudo-elements (::-webkit-scrollbar, track, thumb, corner) to `frontend/src/globals.css`
- [X] T008 [US1] Add scrollbar thumb hover state styles to `frontend/src/globals.css`
- [X] T009 [US1] Verify scrollbar styling on main content area in `frontend/src/components/layout/MainLayout.tsx`
- [X] T010 [US1] Cross-browser visual test: Chrome, Firefox, Safari, Edge (manual verification)

**Checkpoint**: Scrollbars should now blend with dark theme across all browsers

---

## Phase 4: User Story 2 - Design Token Compliance Audit (Priority: P2)

**Goal**: Replace all hardcoded colors with design tokens in component files

**Independent Test**: Run grep search for hardcoded color patterns and confirm zero violations in component files

### Implementation for User Story 2

- [X] T011 [P] [US2] Update badge `success` variant to use token-based colors in `frontend/src/components/ui/badge.tsx`
- [X] T012 [P] [US2] Update badge `muted` variant to use `bg-muted text-muted-foreground` in `frontend/src/components/ui/badge.tsx`
- [X] T013 [P] [US2] Update badge `info` variant to use token-based colors in `frontend/src/components/ui/badge.tsx`
- [X] T014 [P] [US2] Add subtle background to alert `destructive` variant (`bg-destructive/10`) in `frontend/src/components/ui/alert.tsx`
- [X] T015 [US2] Audit and fix any remaining hardcoded colors in `frontend/src/components/ui/` directory
- [X] T016 [US2] Run final grep verification to confirm zero hardcoded color violations

**Checkpoint**: All components should now use design tokens exclusively

---

## Phase 5: User Story 3 - Sufficient Contrast for Accessibility (Priority: P2)

**Goal**: Ensure all text/UI elements meet WCAG 2.1 AA contrast requirements

**Independent Test**: Run Lighthouse accessibility audit and confirm zero contrast violations

### Implementation for User Story 3

- [X] T017 [US3] Run Lighthouse accessibility audit on main pages (Collections, Connectors, Dashboard)
- [X] T018 [US3] Document any contrast violations found and fix them in respective component files
- [X] T019 [P] [US3] Verify focus ring visibility on buttons in `frontend/src/components/ui/button.tsx`
- [X] T020 [P] [US3] Verify focus ring visibility on inputs in `frontend/src/components/ui/input.tsx`
- [X] T021 [US3] Re-run Lighthouse audit to confirm zero contrast violations

**Checkpoint**: All text and UI elements should pass WCAG AA contrast requirements

---

## Phase 6: User Story 4 - Form Input Styling (Priority: P3)

**Goal**: Verify all form controls follow dark theme styling using design tokens

**Independent Test**: Navigate to Create Collection/Connector forms and verify all inputs, selects, textareas use dark theme styling

### Implementation for User Story 4

- [X] T022 [P] [US4] Verify input styling uses design tokens in `frontend/src/components/ui/input.tsx`
- [X] T023 [P] [US4] Verify textarea styling uses design tokens in `frontend/src/components/ui/textarea.tsx`
- [X] T024 [P] [US4] Verify select/dropdown styling uses design tokens in `frontend/src/components/ui/select.tsx`
- [X] T025 [P] [US4] Verify checkbox styling uses design tokens in `frontend/src/components/ui/checkbox.tsx`
- [X] T026 [US4] Verify FormMessage error styling has sufficient contrast in `frontend/src/components/ui/form.tsx`
- [X] T027 [US4] Visual test: Navigate through all forms and verify dark theme consistency

**Checkpoint**: All form controls should match dark theme styling

---

## Phase 7: User Story 5 - Error State Visibility and Graceful Degradation (Priority: P2)

**Goal**: Implement styled error boundaries, 404 page, and consistent error messages with proper dark theme styling

**Independent Test**: Stop backend, navigate to invalid routes, trigger API failures - verify all error states display readable, styled messages

### Tests for User Story 5

- [X] T028 [P] [US5] Write unit test for ErrorBoundary component in `frontend/tests/components/error/ErrorBoundary.test.tsx`

### Implementation for User Story 5

- [X] T029 [P] [US5] Create ErrorBoundary class component in `frontend/src/components/error/ErrorBoundary.tsx`
- [X] T030 [P] [US5] Create ErrorFallback functional component with dark theme styling in `frontend/src/components/error/ErrorFallback.tsx`
- [X] T031 [US5] Create NotFoundPage component with dark theme styling in `frontend/src/pages/NotFoundPage.tsx`
- [X] T032 [US5] Add catch-all route for 404 in `frontend/src/App.tsx`
- [X] T033 [US5] Wrap App with root ErrorBoundary in `frontend/src/App.tsx`
- [X] T034 [US5] Create barrel export file in `frontend/src/components/error/index.ts`
- [X] T035 [US5] Test error boundary by simulating component failure (verified via unit tests - 7/7 passing)
- [X] T036 [US5] Test 404 page by navigating to invalid route
- [X] T037 [US5] Test API error display by stopping backend and loading a data page

**Checkpoint**: All error states should display readable, dark-themed messages with recovery options

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and final verification

- [X] T038 [P] Update design-system.md with scrollbar styling guidelines in `frontend/docs/design-system.md`
- [X] T039 [P] Document known exceptions (native browser controls) in `frontend/docs/design-system.md`
- [X] T040 Run full quickstart.md verification checklist from `specs/009-dark-theme-compliance/quickstart.md`
- [X] T041 Final cross-browser visual inspection (Chrome, Firefox, Safari, Edge)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Scrollbars) should complete first as it's the primary issue
  - US2-US5 can proceed in priority order or parallel
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Scrollbars)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2 - Token Audit)**: Can start after Foundational - Independent of other stories
- **User Story 3 (P2 - Contrast)**: Can start after US2 (needs token fixes first for accurate audit)
- **User Story 4 (P3 - Forms)**: Can start after Foundational - Independent of other stories
- **User Story 5 (P2 - Errors)**: Can start after Foundational - Independent of other stories

### Within Each User Story

- CSS/global changes before component-specific changes
- Component updates before visual verification
- All implementation before cross-browser testing

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- Badge variant updates (T011, T012, T013) can run in parallel
- Alert update (T014) can run in parallel with badge updates
- Form component verifications (T022-T025) can run in parallel
- Error component creation (T029, T030) can run in parallel
- Focus ring verifications (T019, T020) can run in parallel
- Documentation updates (T038, T039) can run in parallel

---

## Parallel Example: User Story 2

```bash
# Launch all badge variant updates together:
Task: "Update badge success variant in frontend/src/components/ui/badge.tsx"
Task: "Update badge muted variant in frontend/src/components/ui/badge.tsx"
Task: "Update badge info variant in frontend/src/components/ui/badge.tsx"

# Launch alert update in parallel:
Task: "Add subtle background to alert destructive variant in frontend/src/components/ui/alert.tsx"
```

## Parallel Example: User Story 5

```bash
# Launch error component creation together:
Task: "Create ErrorBoundary class component in frontend/src/components/error/ErrorBoundary.tsx"
Task: "Create ErrorFallback functional component in frontend/src/components/error/ErrorFallback.tsx"
Task: "Write unit test for ErrorBoundary in frontend/tests/components/error/ErrorBoundary.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (audit baseline)
2. Complete Phase 2: Foundational (add tokens, global scrollbar styles)
3. Complete Phase 3: User Story 1 (scrollbar styling)
4. **STOP and VALIDATE**: Test scrollbars across browsers
5. This alone resolves the primary issue from GitHub Issue #55

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Scrollbars) → Visual test → Primary fix done!
3. Add User Story 2 (Token Audit) → Grep verification → Zero hardcoded colors
4. Add User Story 3 (Contrast) → Lighthouse audit → WCAG compliant
5. Add User Story 4 (Forms) → Visual test → Forms consistent
6. Add User Story 5 (Errors) → Error simulation → Graceful error handling
7. Polish → Documentation complete

### Single Developer Strategy

Recommended order (sequential by priority):

1. Phases 1-2: Setup + Foundational (required)
2. Phase 3: User Story 1 - Scrollbars (P1 - primary issue)
3. Phase 4: User Story 2 - Token Audit (P2 - root cause fix)
4. Phase 7: User Story 5 - Error States (P2 - new components)
5. Phase 5: User Story 3 - Contrast (P2 - verification)
6. Phase 6: User Story 4 - Forms (P3 - verification/polish)
7. Phase 8: Polish

---

## Notes

- [P] tasks = different files, no dependencies within that group
- [Story] label maps task to specific user story for traceability
- Each user story can be independently completed and tested
- Badge changes are to the SAME file but different variant sections - mark [P] as they're distinct code blocks
- Visual verification tasks cannot be parallelized (sequential browser testing)
- Commit after each phase completion for clean history
- Stop at any checkpoint to validate story independently
