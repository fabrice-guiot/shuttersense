# Tasks: Mobile Responsive Tables and Tabs

**Input**: Design documents from `/specs/123-mobile-responsive-tables-tabs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit tests included for the two new foundational components (`ResponsiveTable`, `ResponsiveTabsList`) per constitution principle II (Testing & Quality). Migration tasks are mechanical and covered by visual QA in Phase 8.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/` for all source files
- **Docs**: `frontend/docs/` for design system documentation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project setup needed — this feature adds components to an existing frontend project. Proceed directly to foundational components.

---

## Phase 2: Foundational (Core Components)

**Purpose**: Create the two reusable responsive components that ALL user stories depend on, plus unit tests. No user story migration can begin until both components exist and pass tests.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 [P] Create `ResponsiveTable` component with `ColumnDef<T>` interface, dual desktop/mobile rendering, and card role system (title, subtitle, badge, detail, action, hidden) in `frontend/src/components/ui/responsive-table.tsx`. Desktop view: standard `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableCell` wrapped in `hidden md:block`. Mobile view: card list wrapped in `md:hidden`. Cards render title+badge top row, subtitle below, detail key-value rows with border separator, action row at bottom with border separator. Default `cardRole` to `detail`. Handle empty state via `emptyState` prop. Conditionally omit badge area if no badge columns, omit action separator if no action columns. Mobile card action row MUST ensure touch targets >= 44px (FR-012) — apply `min-h-11` (44px) to action buttons or use `size="sm"` with padding that meets the 44px minimum. See `contracts/component-api.md` for full interface and `data-model.md` for `ColumnDef<T>` and `ResponsiveTableProps<T>` fields.
- [x] T002 [P] Create `ResponsiveTabsList` component with `TabOption` interface in `frontend/src/components/ui/responsive-tabs-list.tsx`. Desktop view: `TabsList` with `hidden md:inline-flex` wrapping `children` (TabsTrigger elements). Mobile view: `Select` dropdown with `md:hidden` rendering `TabOption` items with icon and badge support. Accept `tabs`, `value`, `onValueChange`, and `children` props. The `Select` calls `onValueChange` to sync with the parent `Tabs` controlled state. See `contracts/component-api.md` for full interface and `data-model.md` for `TabOption` and `ResponsiveTabsListProps` fields.
- [x] T003 [P] Write unit tests for `ResponsiveTable` in `frontend/src/components/ui/__tests__/responsive-table.test.tsx`. Test cases: (1) renders `<table>` element inside `hidden md:block` wrapper for desktop view, (2) renders card list inside `md:hidden` wrapper for mobile view, (3) columns with `cardRole: 'title'` render as bold text in card header, (4) columns with `cardRole: 'badge'` render in the title row's right-aligned area, (5) columns with `cardRole: 'hidden'` do not appear in card view, (6) columns with no explicit `cardRole` default to `detail` and render as key-value rows, (7) `cardRole: 'action'` columns render in a bottom action row with border separator, (8) action row and separator are omitted when no action columns exist, (9) badge area is omitted when no badge columns exist, (10) `emptyState` prop renders when data array is empty, (11) renders nothing when data is empty and no `emptyState` provided. Use React Testing Library with `render()` and query by role/text.
- [x] T004 [P] Write unit tests for `ResponsiveTabsList` in `frontend/src/components/ui/__tests__/responsive-tabs-list.test.tsx`. Test cases: (1) renders `<Select>` inside `md:hidden` wrapper for mobile view, (2) renders `TabsList` inside `hidden md:inline-flex` wrapper for desktop view, (3) all `TabOption` items appear as `SelectItem` elements in the dropdown, (4) icons render inside `SelectItem` when provided in `TabOption`, (5) badges render inside `SelectItem` when provided in `TabOption`, (6) calling `onValueChange` from `Select` fires the handler with the selected tab value, (7) `children` (TabsTrigger elements) render inside the desktop `TabsList`. Use React Testing Library with `render()` and query by role/text.

**Checkpoint**: Both components render correctly in isolation and all unit tests pass. Desktop view matches standard table/tabs. Mobile view renders cards/select.

---

## Phase 3: User Story 1 — View Table Data on a Mobile Phone (Priority: P1)

**Goal**: Migrate the first table to `ResponsiveTable` to prove the component works end-to-end with a real table. Use `CollectionList` as the pilot — it has 9 columns covering all card roles, includes tabs (needed for US4), and is the most visited page.

**Independent Test**: Open Collections page at 375px width. All data visible as cards without horizontal scrolling. At 768px+, standard table renders identically to pre-migration.

### Implementation for User Story 1

- [x] T005 [US1] Migrate `CollectionList` table to `ResponsiveTable` in `frontend/src/components/collections/CollectionList.tsx`. Define `ColumnDef` array with card role mappings: Name=title, Location=subtitle, Type+State=badge, Agent+Pipeline+Inventory+Status=detail, Edit+Delete=action. Replace the existing `<div className="rounded-md border ..."><Table>...</Table></div>` pattern with `<ResponsiveTable data={...} columns={columns} keyField="guid" emptyState={...} />`. Preserve all existing cell render logic (badges, icons, tooltips, trend indicators). Verify desktop rendering is unchanged.

**Checkpoint**: Collections page renders cards on mobile, table on desktop. All column data visible in card layout. Empty states work. This validates the `ResponsiveTable` component with a real-world table.

---

## Phase 4: User Story 2 — Navigate Tabs on a Mobile Phone (Priority: P1)

**Goal**: Migrate the first tab strip to `ResponsiveTabsList` to prove the component works with controlled tabs. Use `SettingsPage` as the pilot — it has 6 tabs (most complex case), admin badges, and icons.

**Independent Test**: Open Settings page at 375px width. All 6 tabs reachable via select dropdown. Tab selection changes content panel and URL parameter. At 768px+, standard tab strip renders identically to pre-migration.

### Implementation for User Story 2

- [x] T006 [US2] Migrate `SettingsPage` tabs to `ResponsiveTabsList` in `frontend/src/pages/SettingsPage.tsx`. Build `TabOption[]` array from the existing `tabs` config: map `tab.id` to `value`, `tab.label` to `label`, `tab.icon` to `icon`, and `tab.superAdminOnly` to badge (render `<Badge variant="secondary">Admin</Badge>` when true). Replace `<TabsList>` with `<ResponsiveTabsList tabs={tabOptions} value={validTab} onValueChange={handleTabChange}>`. Keep existing `TabsTrigger` children inside as the desktop rendering. Verify URL sync continues to work via `onValueChange`.

**Checkpoint**: Settings page shows select picker on mobile with all 6 tabs including Admin badges. Tab switching works from both select and desktop triggers. URL parameter updates correctly.

---

## Phase 5: User Story 3 — Migrate All Existing Tables to Responsive Component (Priority: P2)

**Goal**: Migrate all remaining 10 tables to `ResponsiveTable` with correct card role mappings per the PRD contract table.

**Independent Test**: Per-page verification at 375px and 768px. Each table renders cards on mobile with correct role assignments. Desktop rendering unchanged for all pages.

### Implementation for User Story 3

- [x] T007 [P] [US3] Migrate `ResultsTable` to `ResponsiveTable` in `frontend/src/components/results/ResultsTable.tsx`. Card roles: Collection=title, Connector=subtitle, Tool+Status=badge, Pipeline+Files+Issues+Duration+Completed=detail, View+Download+Delete=action. Also update the pagination bar CSS from `flex items-center justify-between` to `flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between` to stack vertically on mobile (FR-011).
- [x] T008 [P] [US3] Migrate `LocationsTab` table to `ResponsiveTable` in `frontend/src/components/directory/LocationsTab.tsx`. Card roles: Name=title, Location=subtitle, Status=badge, Category+Rating+Instagram=detail, Edit+Delete=action, Created=hidden.
- [x] T009 [P] [US3] Migrate `OrganizersTab` table to `ResponsiveTable` in `frontend/src/components/directory/OrganizersTab.tsx`. Card roles: Name=title, Status=badge, Event Count+Rating+Category+Instagram=detail, Edit+Delete=action, Created=hidden.
- [x] T010 [P] [US3] Migrate `PerformersTab` table to `ResponsiveTable` in `frontend/src/components/directory/PerformersTab.tsx`. Card roles: Name=title, Status=badge, Event Count+Rating+Category+Social=detail, Edit+Delete=action, Created=hidden.
- [x] T011 [P] [US3] Migrate `AgentsPage` table to `ResponsiveTable` in `frontend/src/pages/AgentsPage.tsx`. Card roles: Name=title, Hostname+OS=subtitle, Status=badge, Load+Version+Last Heartbeat=detail, Menu(dropdown)=action. The existing `DropdownMenu` action pattern renders naturally in the card action row.
- [x] T012 [P] [US3] Migrate `CategoriesTab` table to `ResponsiveTable` in `frontend/src/components/settings/CategoriesTab.tsx`. Card roles: Name=title, Color+Icon+Status=badge, Event Count=detail, Edit+Delete=action, Created=hidden.
- [x] T013 [P] [US3] Migrate `ConnectorList` table to `ResponsiveTable` in `frontend/src/components/connectors/ConnectorList.tsx`. Card roles: Name=title, Type+Status=badge, Credentials+Created=detail, Test+Edit+Delete=action.
- [x] T014 [P] [US3] Migrate `TokensTab` table to `ResponsiveTable` in `frontend/src/components/settings/TokensTab.tsx`. Card roles: Name=title, Prefix=subtitle, Status=badge, Created+Expires=detail, Delete=action.
- [x] T015 [P] [US3] Migrate `TeamsTab` table to `ResponsiveTable` in `frontend/src/components/settings/TeamsTab.tsx`. Card roles: Team=title, Slug=subtitle, Status=badge, Users=detail, Edit+Delete=action.
- [x] T016 [P] [US3] Migrate `ReleaseManifestsTab` table to `ResponsiveTable` in `frontend/src/components/settings/ReleaseManifestsTab.tsx`. Card roles: Version=title, Release Date=subtitle, Status=badge, Actions=action.

**Checkpoint**: All 11 tables (including T005 from US1) now use `ResponsiveTable`. Every page renders cards on mobile, standard table on desktop. No visual regressions at 768px+.

---

## Phase 6: User Story 4 — Migrate All Existing Tab Strips to Responsive Component (Priority: P2)

**Goal**: Migrate all remaining 5 tab instances (plus 1 nested sub-tab) to `ResponsiveTabsList`. Convert `CollectionList` tabs from uncontrolled to controlled.

**Independent Test**: Per-page verification at 375px and 768px. Each tab set renders select picker on mobile with all tabs reachable. Desktop tab strip unchanged.

### Implementation for User Story 4

- [x] T017 [P] [US4] Convert `CollectionList` tabs from uncontrolled to controlled and migrate to `ResponsiveTabsList` in `frontend/src/components/collections/CollectionList.tsx`. Add `const [activeTab, setActiveTab] = useState("all")`. Replace `<Tabs defaultValue="all">` with `<Tabs value={activeTab} onValueChange={setActiveTab}>`. Build `TabOption[]` array with values "all", "recent", "archived" (label-only, no icons). Replace `<TabsList>` with `<ResponsiveTabsList>` wrapping existing `TabsTrigger` children.
- [x] T018 [P] [US4] Migrate `AnalyticsPage` main tabs to `ResponsiveTabsList` in `frontend/src/pages/AnalyticsPage.tsx`. Build `TabOption[]` from the 4 main tabs (trends, reports, runs, storage) with their icons (TrendingUp, FileText, Clock, HardDrive). Replace `<TabsList>` with `<ResponsiveTabsList tabs={...} value={activeTab} onValueChange={handleTabChange}>`. Preserve the outer flex container that places action buttons alongside tabs — the `ResponsiveTabsList` replaces only the `TabsList` inside it.
- [x] T019 [US4] Migrate `AnalyticsPage` nested runs sub-tabs to `ResponsiveTabsList` in `frontend/src/pages/AnalyticsPage.tsx`. Build `TabOption[]` from the 4 sub-tabs (upcoming, active, completed, failed) with their icons and count badges (e.g., `(queueStatus.upcoming_count)`). Replace the nested `<TabsList>` with `<ResponsiveTabsList>`. Count badges render as inline text within `SelectItem`. Depends on T018 since both are in the same file — implement nested tabs after main tabs.
- [x] T020 [P] [US4] Migrate `DirectoryPage` tabs to `ResponsiveTabsList` in `frontend/src/pages/DirectoryPage.tsx`. Build `TabOption[]` from the 3 tabs (locations, organizers, performers) with their icons. Replace `<TabsList>` with `<ResponsiveTabsList tabs={...} value={validTab} onValueChange={handleTabChange}>`. Verify URL sync works.

**Checkpoint**: All 6 tab instances (5 top-level + 1 nested) use `ResponsiveTabsList`. Select picker on mobile, tab strip on desktop. CollectionList tabs now controlled. All URL-synced tabs continue working.

---

## Phase 7: User Story 5 — Update Design System Documentation (Priority: P3)

**Goal**: Document the new responsive table and tab components in the design system so future development follows the established patterns.

**Independent Test**: Review design system documentation for completeness. New "Table Responsiveness" and "Tab Responsiveness" sections exist with usage patterns, card role conventions, and mandatory usage requirements.

### Implementation for User Story 5

- [x] T021 [US5] Add "Table Responsiveness" section to `frontend/docs/design-system.md`. Document: `ResponsiveTable` component import and usage, `ColumnDef<T>` interface with all `cardRole` values, card layout structure (title/subtitle/badge/detail/action/hidden zones), recommended card role mappings per domain, empty state handling, and the requirement that all new tables MUST use `<ResponsiveTable>`.
- [x] T022 [US5] Add "Tab Responsiveness" section to `frontend/docs/design-system.md`. Document: `ResponsiveTabsList` component import and usage, `TabOption` interface, controlled tabs requirement, integration with Radix UI `Tabs`, `Select` dropdown behavior on mobile, flex container compatibility for tabs with action buttons, and the requirement that all new tab sets MUST use `<ResponsiveTabsList>`.

**Checkpoint**: Design system documentation complete. Future developers have clear guidance on responsive table and tab patterns.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all migrated pages

- [x] T023 Verify TypeScript compilation succeeds with no errors across all modified files by running `npm run build` in `frontend/`
- [x] T024 Visual QA pass at 375px (iPhone SE), 390px (iPhone 14), and 412px (Pixel) viewports across all 11 table pages and 5 tabbed pages. Verify: cards render without horizontal scroll, select pickers show all tabs, action buttons have touch targets >= 44px (FR-012), pagination stacks vertically, no layout breakage. Also verify edge cases: cards with no action columns omit action separator, cards with no badge columns collapse badge area, long tab labels display without truncation in select dropdown.
- [x] T025 Desktop regression check at 1024px and 1440px viewports across all modified pages. Verify: table rendering identical to pre-migration, tab strips identical to pre-migration, no visual changes at md breakpoint and above

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — can start immediately
- **User Story 1 (Phase 3)**: Depends on T001, T003 (`ResponsiveTable` component + tests)
- **User Story 2 (Phase 4)**: Depends on T002, T004 (`ResponsiveTabsList` component + tests)
- **User Story 3 (Phase 5)**: Depends on T001, T003 (`ResponsiveTable` component + tests) — can run in parallel with US1/US2/US4
- **User Story 4 (Phase 6)**: Depends on T002, T004 (`ResponsiveTabsList` component + tests) — can run in parallel with US1/US2/US3
- **User Story 5 (Phase 7)**: Depends on T001 and T002 (needs to document finalized APIs)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on T001, T003. Independent of US2/US3/US4/US5.
- **US2 (P1)**: Depends on T002, T004. Independent of US1/US3/US4/US5.
- **US3 (P2)**: Depends on T001, T003. Independent of US2/US4/US5. Can run in parallel with US1 (different files).
- **US4 (P2)**: Depends on T002, T004. Independent of US1/US3/US5. Can run in parallel with US2 (different files except AnalyticsPage).
  - T019 depends on T018 (same file: AnalyticsPage.tsx — nested tabs after main tabs).
- **US5 (P3)**: Depends on T001 and T002 completion to document finalized APIs.

### Within Each User Story

- All [P]-marked migration tasks within US3 and US4 can run in parallel (different files)
- T019 (nested sub-tabs) must follow T018 (main tabs) in US4 — same file

### Parallel Opportunities

- T001, T002, T003, T004 can run in parallel (Phase 2 — different files)
- After Phase 2: US1 + US2 + US3 + US4 can all start in parallel
- Within US3: All 10 table migrations (T007–T016) can run in parallel
- Within US4: T017, T018, T020 can run in parallel; T019 follows T018
- T021 and T022 (US5) can run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```
# All foundational tasks can be built in parallel:
Task T001: "Create ResponsiveTable component in frontend/src/components/ui/responsive-table.tsx"
Task T002: "Create ResponsiveTabsList component in frontend/src/components/ui/responsive-tabs-list.tsx"
Task T003: "Unit tests for ResponsiveTable in frontend/src/components/ui/__tests__/responsive-table.test.tsx"
Task T004: "Unit tests for ResponsiveTabsList in frontend/src/components/ui/__tests__/responsive-tabs-list.test.tsx"
```

## Parallel Example: User Story 3 (All Table Migrations)

```
# All 10 remaining table migrations can run simultaneously:
Task T007: "Migrate ResultsTable in frontend/src/components/results/ResultsTable.tsx"
Task T008: "Migrate LocationsTab in frontend/src/components/directory/LocationsTab.tsx"
Task T009: "Migrate OrganizersTab in frontend/src/components/directory/OrganizersTab.tsx"
Task T010: "Migrate PerformersTab in frontend/src/components/directory/PerformersTab.tsx"
Task T011: "Migrate AgentsPage in frontend/src/pages/AgentsPage.tsx"
Task T012: "Migrate CategoriesTab in frontend/src/components/settings/CategoriesTab.tsx"
Task T013: "Migrate ConnectorList in frontend/src/components/connectors/ConnectorList.tsx"
Task T014: "Migrate TokensTab in frontend/src/components/settings/TokensTab.tsx"
Task T015: "Migrate TeamsTab in frontend/src/components/settings/TeamsTab.tsx"
Task T016: "Migrate ReleaseManifestsTab in frontend/src/components/settings/ReleaseManifestsTab.tsx"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 2: Foundational (T001–T004 in parallel)
2. Complete Phase 3: US1 — Collections table migration (T005)
3. Complete Phase 4: US2 — Settings tabs migration (T006)
4. **STOP and VALIDATE**: Test mobile table cards and tab select picker on Collections and Settings pages
5. Deploy/demo if ready — these two pages cover the most critical mobile UX issues

### Full Delivery

1. Complete foundational components + tests (Phase 2)
2. Complete US1 + US2 (Phases 3–4) → Test independently → MVP ready
3. Complete US3 (Phase 5) → All tables responsive → Test each page
4. Complete US4 (Phase 6) → All tabs responsive → Test each page
5. Complete US5 (Phase 7) → Documentation updated
6. Complete Phase 8 → Full visual QA pass

### Parallel Team Strategy

With 2 developers after Phase 2:
- **Developer A**: US1 (T005) → US3 (T007–T016)
- **Developer B**: US2 (T006) → US4 (T017–T020) → US5 (T021–T022)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group (e.g., commit each table migration individually)
- Stop at any checkpoint to validate story independently
- Unit tests cover the two new foundational components per constitution principle II (Testing & Quality)
- All migrations are mechanical: define ColumnDef/TabOption arrays, replace Table/TabsList wrapper, preserve existing cell/trigger render logic
