# Tasks: Page Layout Cleanup

**Input**: Design documents from `/specs/015-page-layout-cleanup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Not explicitly requested in feature specification. Visual testing recommended during implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/` for all changes (frontend-only feature)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend core components to support the layout cleanup

- [x] T001 Add `pageHelp?: string` to TopHeaderProps interface in `frontend/src/components/layout/TopHeader.tsx`
- [x] T002 Add `pageHelp?: string` to MainLayoutProps interface in `frontend/src/components/layout/MainLayout.tsx`
- [x] T003 Add `pageHelp?: string` to RouteConfig interface in `frontend/src/App.tsx`
- [x] T004 Pass pageHelp from MainLayout to TopHeader in `frontend/src/components/layout/MainLayout.tsx`

---

## Phase 2: User Story 1 - Clean Single-Title Page Experience (Priority: P1) MVP

**Goal**: Remove duplicate page titles from all pages, consolidating to single TopHeader title

**Independent Test**: Navigate to any page and verify only one page title is visible (in TopHeader band), with no duplicate in content area

### Implementation for User Story 1

- [x] T005 [P] [US1] Remove h1 title and wrapper div from CollectionsPage in `frontend/src/pages/CollectionsPage.tsx` (lines ~131-139)
- [x] T006 [P] [US1] Remove h1 title and wrapper div from ConnectorsPage in `frontend/src/pages/ConnectorsPage.tsx` (lines ~101-109)
- [x] T007 [P] [US1] Remove h1 title and wrapper div from AnalyticsPage in `frontend/src/pages/AnalyticsPage.tsx` (lines ~391-405)
- [x] T008 [P] [US1] Remove h1 title, icon, and description from SettingsPage in `frontend/src/pages/SettingsPage.tsx` (lines ~63-73)
- [x] T009 [P] [US1] Remove h1 title and wrapper div from EventsPage in `frontend/src/pages/EventsPage.tsx` (lines ~283-290)
- [x] T009b [P] [US1] Remove h1 title, icon, and description from DirectoryPage in `frontend/src/pages/DirectoryPage.tsx` (lines ~66-77)
- [x] T009c [P] [US1] Remove h2 title and description from ConnectorsTab in `frontend/src/components/settings/ConnectorsTab.tsx`
- [x] T009d [P] [US1] Remove h2 title and description from CategoriesTab in `frontend/src/components/settings/CategoriesTab.tsx`
- [x] T009e [P] [US1] Remove h2 title and description from ConfigTab in `frontend/src/components/settings/ConfigTab.tsx`
- [x] T009f [P] [US1] Remove h2 title and description from LocationsTab in `frontend/src/components/directory/LocationsTab.tsx`
- [x] T009g [P] [US1] Remove h2 title and description from OrganizersTab in `frontend/src/components/directory/OrganizersTab.tsx`
- [x] T009h [P] [US1] Remove h2 title and description from PerformersTab in `frontend/src/components/directory/PerformersTab.tsx`
- [x] T010 [US1] Visual verification: Confirm all pages show single title in TopHeader only

**Checkpoint**: All pages should now display exactly one title (in TopHeader). Action buttons remain in their original positions temporarily.

---

## Phase 3: User Story 2 - Help Icon for Page Descriptions (Priority: P2)

**Goal**: Add optional help tooltip to TopHeader for pages with descriptive context

**Independent Test**: Hover over help icon on Settings page and verify tooltip displays page description

### Implementation for User Story 2

- [x] T011 [US2] Import HelpCircle icon and Tooltip components in `frontend/src/components/layout/TopHeader.tsx`
- [x] T012 [US2] Add conditional help icon with Tooltip to TopHeader (next to page title) in `frontend/src/components/layout/TopHeader.tsx`
- [x] T013 [US2] Add pageHelp content to Settings and Directory routes in `frontend/src/App.tsx`
- [x] T014 [US2] Test help tooltip appears on hover for Settings page
- [x] T015 [US2] Verify help icon does NOT appear on pages without pageHelp defined

**Checkpoint**: Settings page should show help icon with tooltip. Other pages should NOT show help icon.

---

## Phase 4: User Story 3 - Repositioned Action Buttons with Tabs (Priority: P3)

**Goal**: Reposition action buttons consistently across page types (tabbed vs non-tabbed)

**Independent Test**: Verify action buttons are positioned consistently: integrated with tabs on tabbed pages, top-right on non-tabbed pages

### Implementation for User Story 3

#### Non-tabbed Pages (Pattern A: Action row at top)

- [x] T016 [P] [US3] Reposition "New Collection" button to top-right action row in `frontend/src/pages/CollectionsPage.tsx`
- [x] T017 [P] [US3] Reposition "New Connector" button to top-right action row in `frontend/src/pages/ConnectorsPage.tsx`

#### Tabbed Pages (Pattern B: Actions integrated with TabsList)

- [x] T018 [US3] Integrate Refresh and "Run Tool" buttons with TabsList row in `frontend/src/pages/AnalyticsPage.tsx`
- [x] T019 [US3] Verify Settings page tabs work correctly (no action buttons, tabs-only)

#### Calendar Page (Pattern C: Keep existing position)

- [x] T020 [US3] Verify "New Event" button position in EventsPage works well in `frontend/src/pages/EventsPage.tsx` (likely no change needed - button is in calendar header)

**Checkpoint**: All pages should have consistently positioned action buttons. Tabbed pages show tabs+actions on same row.

---

## Phase 5: User Story 4 - Mobile-Optimized Layout (Priority: P4)

**Goal**: Ensure all layout changes work correctly at mobile viewport sizes

**Independent Test**: View each page at 375px width and verify: single title visible, action buttons accessible, no horizontal overflow

### Implementation for User Story 4

- [x] T021 [P] [US4] Test CollectionsPage at mobile breakpoint (375px) - verify layout and button accessibility
- [x] T022 [P] [US4] Test ConnectorsPage at mobile breakpoint (375px) - verify layout and button accessibility
- [x] T023 [P] [US4] Test AnalyticsPage at mobile breakpoint (375px) - verify tabs/actions layout adapts gracefully
- [x] T024 [P] [US4] Test EventsPage at mobile breakpoint (375px) - verify calendar and button layout
- [x] T025 [P] [US4] Test SettingsPage at mobile breakpoint (375px) - verify tabs layout and help icon
- [x] T026 [US4] Test help tooltip tap interaction on mobile (touch instead of hover)
- [x] T027 [US4] Fix any mobile layout issues discovered during testing

**Checkpoint**: All pages should render correctly and be fully functional on mobile devices.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, cleanup, and documentation updates

### Accessibility & Testing

- [x] T028 Test keyboard navigation to help icon (Tab key should reach it, Enter/Space should activate)
- [x] T029 Verify screen reader announces help tooltip content properly
- [x] T030 Test all pages at tablet breakpoint (768px)
- [x] T031 Test all pages at desktop breakpoint (1024px+)

### Code Cleanup

- [x] T032 Code cleanup: Remove any unused imports or comments from modified files
- [x] T033 Run frontend linter and fix any issues: `npm run lint` in `frontend/`

### Documentation Updates

- [x] T034 [P] Update design system documentation with Single Title Pattern section in `frontend/docs/design-system.md`:
  - Document that pages MUST NOT include h1 titles (TopHeader is the single source)
  - Document the pageHelp mechanism for contextual descriptions
  - Document action button positioning patterns (non-tabbed: top-right row, tabbed: integrated with TabsList)
  - Add code examples showing correct page structure

- [x] T035 [P] Update agent documentation in `CLAUDE.md`:
  - Add "Single Title Pattern" to Frontend Architecture section
  - Document that new pages MUST NOT add h1 elements in content area
  - Reference the TopHeader as single source of truth for page titles
  - Document pageHelp prop usage in route configuration

- [x] T036 [P] Update project constitution in `.specify/memory/constitution.md`:
  - Add new Frontend UI Standard: "Single Title Pattern"
  - Require all pages to use TopHeader as the only page title location
  - Require action buttons follow consistent positioning patterns
  - Document the pageHelp mechanism for on-demand page descriptions
  - Increment constitution version (MINOR change - new standard added)

**Checkpoint**: All documentation should reflect the new page layout patterns, ensuring future development follows these standards.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T001-T004) completion
- **User Story 2 (Phase 3)**: Depends on Setup completion (uses pageHelp prop)
- **User Story 3 (Phase 4)**: Depends on US1 completion (titles already removed)
- **User Story 4 (Phase 5)**: Depends on US1, US2, US3 completion (testing final state)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup - Delivers MVP (single title experience)
- **User Story 2 (P2)**: Can start after Setup - Independent of US1, but recommended after to avoid conflicts
- **User Story 3 (P3)**: Requires US1 complete (repositioning makes sense after title removal)
- **User Story 4 (P4)**: Requires US1, US2, US3 complete (testing the final state)

### Within Each User Story

- Tasks marked [P] can run in parallel (different files)
- Verification tasks should run after implementation tasks

### Parallel Opportunities

**Setup Phase:**
- T001, T002, T003 modify different files - can run in parallel

**User Story 1:**
- T005, T006, T007, T008, T009 all modify different page files - can ALL run in parallel

**User Story 3:**
- T016, T017 modify different page files - can run in parallel

**User Story 4:**
- T021, T022, T023, T024, T025 are independent testing tasks - can ALL run in parallel

**Polish Phase (Documentation):**
- T034, T035, T036 modify different documentation files - can ALL run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all page modifications for US1 together (different files):
Task: "Remove h1 from CollectionsPage in frontend/src/pages/CollectionsPage.tsx"
Task: "Remove h1 from ConnectorsPage in frontend/src/pages/ConnectorsPage.tsx"
Task: "Remove h1 from AnalyticsPage in frontend/src/pages/AnalyticsPage.tsx"
Task: "Remove h1 from SettingsPage in frontend/src/pages/SettingsPage.tsx"
Task: "Remove h1 from EventsPage in frontend/src/pages/EventsPage.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: User Story 1 (T005-T010)
3. **STOP and VALIDATE**: Test all pages show single title
4. Deploy/demo if MVP is acceptable

### Incremental Delivery

1. Complete Setup → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP! Single titles)
3. Add User Story 2 → Test → Deploy (Help tooltips)
4. Add User Story 3 → Test → Deploy (Repositioned buttons)
5. Add User Story 4 → Test → Deploy (Mobile verified)
6. Complete Polish → Final release

### Recommended Order for Single Developer

1. T001-T004 (Setup)
2. T005-T010 (US1 - all pages in parallel)
3. T011-T015 (US2 - help mechanism)
4. T016-T020 (US3 - button repositioning)
5. T021-T027 (US4 - mobile testing)
6. T028-T033 (Polish - testing & cleanup)
7. T034-T036 (Polish - documentation updates, can run in parallel)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- US1 is the MVP - delivers core value (single title)
- US2-US4 are enhancements that can be deferred if needed
- Commit after each phase for easy rollback
- Visual testing recommended at each checkpoint
