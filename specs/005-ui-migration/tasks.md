---

description: "Task list for UI Migration to Modern Design System"
---

# Tasks: UI Migration to Modern Design System

**Input**: Design documents from `/specs/005-ui-migration/`
**Prerequisites**: plan.md (tech stack), spec.md (user stories), research.md (decisions), data-model.md (types), contracts/ (interfaces)

**Tests**: Tests are included in Phase 5 as existing tests need to be updated for the new component library. This is NOT test-driven development - tests are migrated alongside implementation.

**Organization**: Tasks are grouped by user story phases to enable independent implementation and testing of each story. This migration follows the 6-phase structure documented in `/specs/004-remote-photos-persistence/ui-migration.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app structure**: `frontend/src/`, `frontend/tests/`
- Backend remains unchanged at `backend/src/`
- All paths shown are absolute from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install and configure Tailwind CSS, shadcn/ui, TypeScript - foundation for all user stories

- [X] T001 Install and configure Tailwind CSS v4 in frontend/package.json and create frontend/tailwind.config.js
- [X] T002 [P] Initialize shadcn/ui via npx and create frontend/components.json configuration
- [X] T003 [P] Create design system CSS variables in frontend/src/globals.css with dark theme tokens
- [X] T004 Install required shadcn/ui components (button, input, table, dialog, badge, select, checkbox, form, etc.)
- [X] T005 [P] Configure TypeScript with frontend/tsconfig.json and path aliases (@/components, @/lib)
- [X] T006 [P] Update frontend/vite.config.ts to support TypeScript and path resolution
- [X] T007 [P] Install form dependencies (react-hook-form, zod, @hookform/resolvers, lucide-react, clsx, tailwind-merge)

**Checkpoint**: ✅ Build passes, Tailwind works, shadcn components available, TypeScript configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core shared utilities and type definitions that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Create frontend/src/lib/utils.ts with cn() helper function for class name merging
- [X] T009 [P] Create frontend/src/types/connector.ts with Connector, ConnectorType, ConnectorCredentials interfaces
- [X] T010 [P] Create frontend/src/types/collection.ts with Collection, CollectionType, CollectionState interfaces
- [X] T011 [P] Create frontend/src/types/api.ts with ApiError, PaginationParams, PaginationMeta interfaces
- [X] T012 Create frontend/src/types/index.ts barrel file exporting all type definitions

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Modern Dark Theme Experience (Priority: P1) 🎯 MVP

**Goal**: Users can access the photo collection management interface with a modern, professional dark theme

**Independent Test**: Load any page and verify dark theme is applied consistently with proper contrast ratios

### Implementation for User Story 1

- [X] T013 [US1] Verify globals.css contains all design tokens from ui-style-proposal (--background, --foreground, --primary, --accent, --sidebar, etc.)
- [X] T014 [US1] Test dark theme CSS variables render correctly in browser DevTools across all defined tokens

**Checkpoint**: Dark theme foundation is in place and visible

---

## Phase 4: User Story 2 - Sidebar Navigation (Priority: P1)

**Goal**: Users can navigate the application using a persistent sidebar with all menu items and active state

**Independent Test**: Load the application and click through all sidebar menu items to verify routing works

### Implementation for User Story 2

- [X] T015 [P] [US2] Create frontend/src/components/layout/Sidebar.tsx with navigation menu items and Lucide icons
- [X] T016 [P] [US2] Create frontend/src/components/layout/TopHeader.tsx with page title, stats, notifications, and user profile
- [X] T017 [US2] Create frontend/src/components/layout/MainLayout.tsx composing Sidebar + TopHeader + content area
- [X] T018 [US2] Rename frontend/src/App.jsx to App.tsx and wrap routes with MainLayout component
- [X] T019 [US2] Add active route detection using useLocation() and highlight active menu item in Sidebar
- [X] T020 [US2] Update page titles in TopHeader dynamically based on current route

**Checkpoint**: New layout renders, navigation works between pages, active states highlight correctly

---

## Phase 5: User Story 3 - Top Header with Context (Priority: P1)

**Goal**: Users see contextual information in top header with page title, metrics, and user profile

**Independent Test**: Navigate to any page and verify header shows correct page title and placeholder metrics

### Implementation for User Story 3

**Note**: Most implementation completed in Phase 4 (US2). This phase verifies header context functionality.

- [X] T021 [US3] Verify TopHeader displays correct page icon and title when navigating to Collections page
- [X] T022 [US3] Add placeholder stats (collection count, storage usage) to TopHeader right section
- [X] T023 [US3] Verify notifications bell icon and user profile with initials display correctly
- [X] T024 [US3] Add hover states to TopHeader interactive elements (notifications, profile dropdown)

**Checkpoint**: Top header provides full contextual information for each page

---

## Phase 6: User Story 4 - Collections List View (Priority: P2)

**Goal**: Users can view and filter photo collections in a table with tabs and filters

**Independent Test**: Load Collections page and interact with tabs, filters, and table to verify all features work

### Implementation for User Story 4

- [X] T025 [P] [US4] Create frontend/src/components/collections/FiltersSection.tsx with state, type, and accessible-only filters
- [X] T026 [P] [US4] Create frontend/src/components/collections/CollectionStatus.tsx to display accessibility badges
- [X] T027 [US4] Migrate frontend/src/components/collections/CollectionList.jsx to .tsx replacing MUI Table with shadcn Table
- [X] T028 [US4] Add tab navigation (All Collections, Recently Accessed, Archived) to CollectionList component
- [X] T029 [US4] Update CollectionList to use FiltersSection component for state/type/accessible filters
- [X] T030 [US4] Add action buttons (Info, RefreshCw, Edit, Trash2) with Lucide icons and tooltips
- [X] T031 [US4] Migrate frontend/src/pages/CollectionsPage.jsx to .tsx with shadcn Dialog for create/edit
- [X] T032 [US4] Update frontend/src/hooks/useCollections.js to .ts with TypeScript types from @/types/collection
- [X] T033 [US4] Update frontend/src/services/collections.js to .ts with typed axios responses

**Checkpoint**: ✅ Collections page fully functional with tabs, filters, table, and all features

---

## Phase 7: User Story 5 - Form Components with Validation (Priority: P2)

**Goal**: Users can create/edit connectors and collections using forms with inline validation and dynamic fields

**Independent Test**: Open create/edit dialogs and submit forms with valid/invalid data to verify validation

### Implementation for User Story 5

- [X] T034 [P] [US5] Create frontend/src/types/schemas/connector.ts with Zod schemas (S3, GCS, SMB credentials)
- [X] T035 [P] [US5] Create frontend/src/types/schemas/collection.ts with Zod CollectionFormSchema
- [X] T036 [US5] Migrate frontend/src/components/connectors/ConnectorForm.jsx to .tsx with shadcn Form + react-hook-form
- [X] T037 [US5] Implement dynamic credential fields in ConnectorForm based on connector type (S3, GCS, SMB)
- [X] T038 [US5] Add Zod validation to ConnectorForm with inline error messages
- [X] T039 [US5] Add Test Connection button to ConnectorForm with loading state and toast feedback
- [X] T040 [US5] Migrate frontend/src/components/connectors/ConnectorList.jsx to .tsx with shadcn components
- [X] T041 [US5] Migrate frontend/src/pages/ConnectorsPage.jsx to .tsx with shadcn Dialog and AlertDialog
- [X] T042 [US5] Update frontend/src/hooks/useConnectors.js to .ts with TypeScript types
- [X] T043 [US5] Update frontend/src/services/connectors.js to .ts with typed axios responses
- [X] T044 [US5] Migrate frontend/src/components/collections/CollectionForm.jsx to .tsx with shadcn Form + react-hook-form
- [X] T045 [US5] Implement dynamic connector dropdown in CollectionForm (hidden for LOCAL, shown for S3/GCS/SMB)
- [X] T046 [US5] Add Zod validation to CollectionForm with connector_id constraints
- [X] T047 [US5] Add Test Connection button to CollectionForm with loading state

**Checkpoint**: ✅ All forms work with validation, dynamic fields, and test connection functionality

---

## Phase 8: User Story 6 - Type Safety and Developer Experience (Priority: P3)

**Goal**: TypeScript type checking prevents errors and improves code maintainability

**Independent Test**: Run `npm run type-check` and verify no TypeScript errors

### Implementation for User Story 6

- [X] T048 [P] [US6] Update frontend/src/services/api.js to .ts with typed axios interceptors and ApiError
- [X] T049 [P] [US6] Rename frontend/src/main.jsx to main.tsx and update imports
- [X] T050 [US6] Add type-check script to frontend/package.json running tsc --noEmit
- [X] T051 [US6] Fix any remaining TypeScript errors across all migrated files
- [X] T052 [US6] Verify IDE autocomplete works correctly for all shadcn components and typed props

**Checkpoint**: ✅ All TypeScript compiles without errors, full type coverage achieved

---

## Phase 9: User Story 7 - Responsive Design (Priority: P3)

**Goal**: Application layouts adapt appropriately to different screen sizes (mobile, tablet, desktop)

**Independent Test**: View application at different viewport widths and verify layout adjusts

### Implementation for User Story 7

- [X] T053 [P] [US7] Test Sidebar component at mobile width (375px) and verify collapse behavior
- [X] T054 [P] [US7] Test Collections table horizontal scroll on mobile viewports
- [X] T055 [P] [US7] Test layout on tablet width (768px) and verify content remains readable
- [X] T056 [US7] Add max-width constraints to content areas for ultra-wide monitors (2560px+)
- [X] T057 [US7] Verify all interactive elements remain accessible via touch on mobile devices

**Checkpoint**: ✅ Application is usable across mobile, tablet, and desktop screen sizes

---

## Phase 10: Testing Migration

**Purpose**: Update all existing tests for shadcn/ui components and TypeScript

**Tests**: Migrating existing test suite to work with new components and types

- [X] T058 [P] Update frontend/vitest.config.js to .ts with TypeScript support and path aliases
- [X] T059 [P] Update frontend/tests/mocks/handlers.js to .ts with typed MSW request handlers
- [X] T060 [P] Create frontend/tests/utils/test-utils.tsx with custom render function for shadcn components
- [X] T061 [P] Update frontend/tests/components/ConnectorForm.test.jsx to .tsx with shadcn Select selectors
- [X] T062 [P] Update frontend/tests/components/ConnectorList.test.jsx to .tsx with shadcn Table and Badge selectors
- [X] T063 [P] Update frontend/tests/components/CollectionForm.test.jsx to .tsx with react-hook-form field selectors
- [X] T064 [P] Update frontend/tests/hooks/useConnectors.test.js to .ts with type assertions
- [X] T065 [P] Update frontend/tests/hooks/useCollections.test.js to .ts with type assertions
- [ ] T066 Update frontend/tests/integration/connector-collection-flow.test.jsx to .tsx with new layout selectors
- [ ] T067 Run full test suite and verify >75% coverage maintained
- [ ] T068 Fix any failing tests related to component selector changes or type mismatches

**Checkpoint**: All tests pass, coverage >75%, TypeScript compiles in test files

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements, optimization, accessibility, and documentation

- [ ] T069 [P] Verify all components use design tokens (bg-background, text-foreground, etc.) with no hardcoded colors
- [ ] T070 [P] Test color contrast ratios with browser DevTools and ensure WCAG AA compliance (4.5:1 for normal text)
- [ ] T071 [P] Test keyboard navigation (Tab, Enter, Escape) across all interactive elements
- [ ] T072 [P] Add aria-label attributes to icon-only buttons for screen reader accessibility
- [ ] T073 Update frontend/vite.config.ts for optimal tree-shaking and chunk splitting
- [ ] T074 [P] Install rollup-plugin-visualizer and generate bundle analysis report
- [ ] T075 Verify MUI is completely removed from bundle (should see ~500KB reduction)
- [ ] T076 [P] Test First Contentful Paint metric (target <1.5s)
- [ ] T077 [P] Uninstall Material-UI dependencies (@mui/material, @emotion/react, etc.) from frontend/package.json
- [ ] T078 Run npm prune and verify package-lock.json updated with MUI removal
- [ ] T079 [P] Update frontend/README.md with new tech stack (Tailwind, shadcn/ui, TypeScript)
- [ ] T080 [P] Create frontend/docs/components.md documenting shadcn component usage patterns
- [ ] T081 Run production build and verify no MUI references in output
- [ ] T082 Test production build locally and verify all functionality works

**Checkpoint**: Production ready, documented, optimized, accessible

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-9)**: All depend on Foundational phase completion
  - US1 (Dark Theme) → US2 (Sidebar) → US3 (Header) can proceed sequentially (US3 builds on US2)
  - US4 (Collections List) can start after US3 (needs layout)
  - US5 (Forms) can start after US4 (needs list components for context)
  - US6 (TypeScript) happens incrementally throughout US1-US5
  - US7 (Responsive) can start after US2-US5 (needs components to test)
- **Testing (Phase 10)**: Can proceed in parallel with US1-US7 or after implementation complete
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Dark Theme)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1 - Sidebar)**: Can start after US1 - Needs dark theme foundation
- **User Story 3 (P1 - Header)**: Depends on US2 - Header is part of MainLayout created in US2
- **User Story 4 (P2 - Collections List)**: Can start after US3 - Needs layout components
- **User Story 5 (P2 - Forms)**: Can start after US4 - Forms integrate with list views
- **User Story 6 (P3 - TypeScript)**: Incremental throughout US1-US5 - No blocking dependencies
- **User Story 7 (P3 - Responsive)**: Can start after US2-US5 - Needs components to make responsive

### Within Each User Story

- Setup and Foundational phases must complete first
- Type definitions before components that use them
- Layout components (Sidebar, TopHeader, MainLayout) before pages
- Components before pages that use them
- Tests update after implementation (not TDD for this migration)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T005, T006, T007)
- All Foundational type definition tasks can run in parallel (T009, T010, T011)
- Within US4: FiltersSection and CollectionStatus components can be built in parallel (T025, T026)
- Within US5: Connector and Collection schemas can be created in parallel (T034, T035)
- All testing tasks in Phase 10 marked [P] can run in parallel (T058-T065)
- All Polish tasks marked [P] can run in parallel (T069-T072, T074, T076, T077, T079, T080)

---

## Parallel Example: User Story 5 (Forms)

```bash
# Launch schema creation tasks in parallel:
Task: "Create frontend/src/types/schemas/connector.ts with Zod schemas"
Task: "Create frontend/src/types/schemas/collection.ts with Zod CollectionFormSchema"

# After schemas complete, these can run in parallel:
Task: "Migrate ConnectorForm.jsx to .tsx with shadcn Form"
Task: "Migrate ConnectorList.jsx to .tsx with shadcn components"
Task: "Update useConnectors.js to .ts with TypeScript types"
Task: "Update connectors service with typed axios responses"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup (7 tasks)
2. Complete Phase 2: Foundational (5 tasks)
3. Complete Phase 3: User Story 1 - Dark Theme (2 tasks)
4. Complete Phase 4: User Story 2 - Sidebar Navigation (6 tasks)
5. Complete Phase 5: User Story 3 - Top Header (4 tasks)
6. **STOP and VALIDATE**: Test layout and navigation independently
7. Deploy/demo if ready

**MVP Deliverable**: Modern dark-themed interface with working navigation

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (12 tasks)
2. Add User Story 1-3 → Test layout → Deploy/Demo (MVP - 12 tasks)
3. Add User Story 4 → Test collections list → Deploy/Demo (9 tasks)
4. Add User Story 5 → Test forms → Deploy/Demo (14 tasks)
5. Add User Story 6 → Verify types → Deploy/Demo (5 tasks)
6. Add User Story 7 → Test responsive → Deploy/Demo (5 tasks)
7. Add Testing & Polish → Production ready (25 tasks)

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (12 tasks)
2. Once Foundational is done:
   - Developer A: User Stories 1-3 (layout foundation) - 12 tasks
   - Developer B: User Story 4 (collections list) - starts after A completes US3 - 9 tasks
   - Developer C: User Story 5 (forms) - starts after B completes US4 - 14 tasks
3. All developers: Testing migration in parallel (11 tasks)
4. All developers: Polish tasks in parallel (14 tasks)

---

## Summary

**Total Tasks**: 82 tasks
- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - Dark Theme): 2 tasks
- Phase 4 (US2 - Sidebar): 6 tasks
- Phase 5 (US3 - Header): 4 tasks
- Phase 6 (US4 - Collections List): 9 tasks
- Phase 7 (US5 - Forms): 14 tasks
- Phase 8 (US6 - TypeScript): 5 tasks
- Phase 9 (US7 - Responsive): 5 tasks
- Phase 10 (Testing): 11 tasks
- Phase 11 (Polish): 14 tasks

**Parallel Opportunities**: 36 tasks marked [P] can run in parallel within their phases

**MVP Scope**: Phases 1-5 (29 tasks) deliver working modern interface with navigation

**Estimated Duration**: 95 hours total (3 weeks for 1 developer)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story builds on previous stories (sequential dependencies)
- Tests are updated after implementation (migration approach, not TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- This is a migration-only feature - maintain 100% functional parity with Material-UI version
- Reference `/specs/004-remote-photos-persistence/ui-migration.md` for detailed implementation guidance
