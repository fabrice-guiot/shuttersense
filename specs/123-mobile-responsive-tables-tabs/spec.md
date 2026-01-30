# Feature Specification: Mobile Responsive Tables and Tabs

**Feature Branch**: `123-mobile-responsive-tables-tabs`
**Created**: 2026-01-29
**Status**: Draft
**Input**: User description: "GitHub issue #123 based on PRD: docs/prd/024-mobile-responsive-tables-tabs.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Table Data on a Mobile Phone (Priority: P1)

A user opens the application on a mobile phone (screen width ~375px). Currently, data tables require horizontal scrolling that hides most columns including action buttons. With this feature, tables automatically transform into a card layout on screens below 768px. Each row becomes a structured card showing the primary identifier at the top, status badges inline, detail rows as labeled key-value pairs, and action buttons at the bottom with adequate touch targets.

**Why this priority**: Tables are the primary data presentation across the entire application (13 instances). Without readable tables, the mobile experience is fundamentally broken. This is the highest-value change.

**Independent Test**: Can be fully tested by opening any table page (e.g., Collections) on a mobile device or at a narrow browser width and verifying all data is visible without horizontal scrolling.

**Acceptance Scenarios**:

1. **Given** a user views the Collections page on a 375px-wide screen, **When** the page loads, **Then** each collection row displays as a card with the name prominently at top, status badges inline, detail rows labeled, and action buttons accessible at the bottom.
2. **Given** a user views any table page at 768px or wider, **When** the page loads, **Then** the standard desktop table layout renders identically to the current behavior.
3. **Given** a table has zero rows, **When** the user views the page on mobile, **Then** the configured empty state displays correctly.
4. **Given** a table column has no explicit card role assigned, **When** rendered on mobile, **Then** it defaults to displaying as a detail key-value row in the card body.

---

### User Story 2 - Navigate Tabs on a Mobile Phone (Priority: P1)

A user opens a tabbed page (e.g., Settings with 6 tabs) on a mobile phone. Currently, tab labels overflow the viewport and break the visual container. With this feature, tab strips are replaced by a dropdown select picker on screens below 768px. The picker shows the active tab label and opens a dropdown with all tab options including icons and badges.

**Why this priority**: Tab navigation is broken on mobile for pages with 4+ tabs (5 instances). Users literally cannot reach all tabs. This is tied with P1 for tables since both are prerequisite for any usable mobile experience.

**Independent Test**: Can be fully tested by opening the Settings page on a mobile device or at a narrow browser width and verifying all tabs are reachable via the dropdown.

**Acceptance Scenarios**:

1. **Given** a user views the Settings page (6 tabs for super admin) on a 375px-wide screen, **When** the page loads, **Then** a dropdown select picker replaces the tab strip, showing the active tab label, icon, and any admin badges.
2. **Given** a user selects a different tab from the mobile dropdown, **When** the selection changes, **Then** the corresponding tab content panel updates immediately and the URL parameter reflects the new tab.
3. **Given** a user views a tabbed page at 768px or wider, **When** the page loads, **Then** the standard desktop tab strip renders identically to the current behavior.
4. **Given** the Analytics page has tabs alongside action buttons, **When** viewed on mobile, **Then** the dropdown and action buttons stack vertically without overlap.

---

### User Story 3 - Migrate All Existing Tables to Responsive Component (Priority: P2)

A developer migrates all 13 existing table instances across the application to use the new responsive table component. Each table gets a card role mapping that defines how columns appear in the mobile card layout: which column is the title, which are badges, which are detail rows, which are actions, and which are hidden on mobile.

**Why this priority**: The core components (P1) only deliver value when applied across all pages. Migration is mechanical but necessary for complete coverage.

**Independent Test**: Can be tested per-page by verifying each migrated table renders correctly in both desktop (unchanged) and mobile (card) views.

**Acceptance Scenarios**:

1. **Given** all 13 tables are migrated, **When** each page is viewed at desktop width, **Then** the table rendering is visually identical to the pre-migration state.
2. **Given** the Results table (10 columns, most complex), **When** viewed on mobile, **Then** it renders as cards with Collection as title, Tool and Status as badges, and View/Download/Delete as action buttons.
3. **Given** the Agents table uses a dropdown menu for actions, **When** viewed on mobile, **Then** the dropdown menu renders correctly in the card action row.

---

### User Story 4 - Migrate All Existing Tab Strips to Responsive Component (Priority: P2)

A developer migrates all 5 tab instances (plus 1 nested sub-tab) to use the new responsive tabs component. The CollectionList tabs must be converted from uncontrolled to controlled mode to support the select picker.

**Why this priority**: Same rationale as Story 3 — the responsive tab component only delivers value when applied to all tabbed pages.

**Independent Test**: Can be tested per-page by verifying each migrated tab set renders correctly in both desktop (unchanged) and mobile (dropdown) views.

**Acceptance Scenarios**:

1. **Given** all 5 tab instances plus the nested runs sub-tab are migrated, **When** each page is viewed at desktop width, **Then** the tab rendering is visually identical to the pre-migration state.
2. **Given** the CollectionList tabs were uncontrolled, **When** migrated to controlled with the responsive component, **Then** tab switching works correctly on both desktop and mobile.
3. **Given** the Analytics page has nested sub-tabs within a tab content panel, **When** viewed on mobile, **Then** the nested sub-tabs also render as a select picker with count badges displayed inline.

---

### User Story 5 - Update Design System Documentation (Priority: P3)

The design system documentation is updated with new sections covering responsive table and tab patterns, card role conventions, and migration guides. All future tables and tab sets are required to use these responsive components.

**Why this priority**: Documentation ensures consistency for future development. Lower priority because it does not affect end-user functionality directly.

**Independent Test**: Can be tested by reviewing the design system documentation for completeness of responsive table, responsive tab, and card role mapping sections.

**Acceptance Scenarios**:

1. **Given** a developer reads the design system docs, **When** they look for table guidance, **Then** a "Table Responsiveness" section documents the responsive table component, card roles, and recommended mappings.
2. **Given** a developer creates a new tabbed page, **When** they consult the design system, **Then** a "Tab Responsiveness" section documents the responsive tabs component and usage patterns.
3. **Given** the design system docs are updated, **When** reviewed, **Then** they explicitly state that all new tables MUST use the responsive table component and all new tab sets MUST use the responsive tabs component.

---

### Edge Cases

- What happens when a table has only 1-2 columns? The card layout should still render cleanly with minimal detail rows.
- What happens when a card has no action columns? The action row separator and section should not render.
- What happens when a card has no badge columns? The badge area should collapse without leaving empty space.
- What happens when a tab label is very long (e.g., "Release Manifests")? The select dropdown must accommodate the full text without truncation.
- What happens when tabs have associated count badges that change dynamically? The select picker should reflect updated badge values reactively.
- How does the pagination bar behave on mobile? It should stack vertically rather than squeezing horizontally.
- What happens when both the table and card DOM nodes are rendered simultaneously (CSS hiding)? Performance should remain acceptable for typical page sizes (up to 50 rows per paginated page).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a reusable responsive table component that renders as a standard table at 768px and above, and as a card list below 768px.
- **FR-002**: System MUST support a column role system with six roles (title, subtitle, badge, detail, action, hidden) that control how each column renders in the mobile card layout.
- **FR-003**: System MUST default columns without an explicit role to "detail" (key-value pair in the card body).
- **FR-004**: System MUST provide a reusable responsive tabs component that renders as a standard tab strip at 768px and above, and as a dropdown select picker below 768px.
- **FR-005**: The responsive tabs component MUST support icons and badges in the dropdown select items to match the desktop tab trigger appearance.
- **FR-006**: The responsive tabs component MUST be compatible with controlled tab state management so the select and tab strip drive the same state.
- **FR-007**: All 13 existing table instances MUST be migrated to use the responsive table component with appropriate card role mappings.
- **FR-008**: All 5 existing tab instances plus 1 nested sub-tab MUST be migrated to use the responsive tabs component.
- **FR-009**: The CollectionList tabs MUST be converted from uncontrolled to controlled mode to support the select picker.
- **FR-010**: Desktop rendering of all migrated pages MUST be visually identical to the pre-migration state (zero regression).
- **FR-011**: Pagination controls MUST stack vertically on mobile to prevent content squeezing.
- **FR-012**: Mobile card action buttons MUST provide adequate touch targets (minimum 44px).
- **FR-013**: The responsive table MUST render the configured empty state when the data array is empty.
- **FR-014**: The responsive tabs component MUST work alongside action buttons in flex containers without layout conflicts.
- **FR-015**: Design system documentation MUST be updated with responsive table and tab sections, card role conventions, and a requirement that all future tables and tabs use these components.

### Key Entities

- **ColumnDef**: A column definition that pairs a header label, a cell render function, and a card role that determines mobile layout positioning (title, subtitle, badge, detail, action, or hidden).
- **TabOption**: A tab definition containing a value identifier, display label, optional icon, and optional badge content for the mobile select picker.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All table data is visible without horizontal scrolling on screens 320px and wider.
- **SC-002**: All tab options are reachable in a single interaction (one tap to open dropdown, one tap to select) on any viewport width.
- **SC-003**: All 13 table instances and all 6 tab instances across the application use the responsive components.
- **SC-004**: Desktop rendering of all pages is visually identical before and after migration — zero visual regressions at 768px and above.
- **SC-005**: Mobile card action buttons have touch targets of at least 44px.
- **SC-006**: Both responsive components are documented in the design system with clear usage guidelines and card role mapping conventions.
- **SC-007**: A user can complete common tasks (view collection details, navigate settings tabs, review analysis results) entirely on a mobile device without horizontal scrolling or layout breakage.

## Assumptions

- The 768px breakpoint is the correct switch point, consistent with existing responsive patterns in the codebase.
- CSS-based toggling is used rather than programmatic viewport detection, keeping both DOM nodes rendered. This is acceptable for typical paginated page sizes (up to 50 rows).
- All tabbed pages except CollectionList already use controlled tabs, so migration only requires wrapping the existing tab strip.
- The card role mappings defined in the PRD (per-table column-to-role assignments) are accepted as the correct mobile layout for each table.
- Individual labeled action buttons are used on mobile cards (rather than consolidated dropdown menus) unless the desktop table already uses a dropdown pattern (e.g., Agents page).
