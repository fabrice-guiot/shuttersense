# Feature Specification: Page Layout Cleanup - Remove Double Titles

**Feature Branch**: `015-page-layout-cleanup`
**Created**: 2026-01-13
**Status**: Draft
**Input**: User description: "GitHub issue #67 - Improve the layout of Pages by removing the double title"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Single-Title Page Experience (Priority: P1)

As a user navigating the application, I want to see a single, clear page title without duplication so that I can quickly identify which page I'm on without visual clutter.

**Why this priority**: This is the core request - eliminating the redundant double title that wastes screen space and creates a confusing visual hierarchy. It directly addresses the main pain point described in the issue.

**Independent Test**: Can be fully tested by navigating to any page and verifying only one title element identifies the current page. Delivers immediate visual clarity and reduced clutter.

**Acceptance Scenarios**:

1. **Given** a user navigates to any page (Collections, Connectors, Analytics, Events), **When** the page loads, **Then** only one page title is visible (in the TopHeader band) and no duplicate title appears in the content area.

2. **Given** a user is on a page with tabs (e.g., Analytics), **When** viewing the page layout, **Then** the tabs appear at the top of the content area without a redundant title above them.

3. **Given** a user is on a page with action buttons, **When** viewing the page layout, **Then** the action buttons are accessible without being paired with a duplicate page title.

---

### User Story 2 - Help Icon for Page Descriptions (Priority: P2)

As a user unfamiliar with a page's purpose, I want to access helpful context about what the page does so that I can understand the functionality without cluttering the main interface.

**Why this priority**: The current secondary titles sometimes include descriptive text about the page purpose. This valuable context should not be lost but rather made accessible on-demand through a help mechanism.

**Independent Test**: Can be tested by clicking/hovering a help icon on any page and verifying helpful description text appears. Delivers contextual guidance without permanent screen real estate usage.

**Acceptance Scenarios**:

1. **Given** a user is on a page with contextual help available, **When** they hover over or click a help icon in the TopHeader, **Then** a tooltip or popover displays descriptive text about the page's purpose.

2. **Given** a user is on a page without specific help content defined, **When** viewing the TopHeader, **Then** no help icon is displayed (graceful absence rather than empty tooltip).

3. **Given** a user on a mobile device, **When** they tap the help icon, **Then** the help content is displayed in a mobile-friendly manner (e.g., a modal or bottom sheet).

---

### User Story 3 - Repositioned Action Buttons with Tabs (Priority: P3)

As a user on a tabbed page (like Analytics), I want action buttons to be logically positioned near the tabs so that the interface remains clean and actions are contextually located after the title removal.

**Why this priority**: With the secondary title removed, action buttons need a new home. Placing them on the same line as tabs is an efficient use of space and keeps related controls together.

**Independent Test**: Can be tested on the Analytics page by verifying action buttons appear alongside tabs without a separate title row. Delivers streamlined interface with better space utilization.

**Acceptance Scenarios**:

1. **Given** a user is on a tabbed page with action buttons (e.g., Analytics), **When** viewing the page, **Then** action buttons appear on the same row as the tabs (tabs on left, actions on right).

2. **Given** a user is on a non-tabbed page with action buttons, **When** viewing the page, **Then** action buttons appear in a consistent location (aligned right below the TopHeader).

3. **Given** a user resizes the browser to a narrow width, **When** viewing a tabbed page with actions, **Then** the layout adapts gracefully (tabs and buttons may stack or buttons may move to a menu).

---

### User Story 4 - Mobile-Optimized Layout (Priority: P4)

As a mobile user, I want the page layout to efficiently use limited screen space so that I can access all functionality without excessive scrolling.

**Why this priority**: The issue explicitly mentions mobile views being problematic with the double title. While this is addressed by P1, ensuring the mobile experience is explicitly considered helps verify the solution works across all viewports.

**Independent Test**: Can be tested by viewing any page on a mobile viewport and verifying no redundant titles appear and all actions remain accessible.

**Acceptance Scenarios**:

1. **Given** a user views any page on a mobile device, **When** the page loads, **Then** the layout uses a single title in the header with action buttons accessible via appropriate mobile patterns.

2. **Given** a user on mobile needs to access page actions, **When** viewing a page with multiple action buttons, **Then** buttons are either visible inline or accessible via a contextual menu.

---

### Edge Cases

- What happens when a page has no descriptive help text defined? The help icon should not appear rather than showing an empty tooltip.
- How does the layout behave when tabs wrap to multiple lines on narrow viewports? Tabs should remain usable and action buttons should adapt gracefully.
- What happens when the TopHeader title is very long? Titles should truncate with ellipsis on narrow screens while remaining fully visible on wider screens.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a single page title in the TopHeader band, removing duplicate titles from page content areas.
- **FR-002**: System MUST preserve all existing action buttons with accessible placement after title removal.
- **FR-003**: System MUST provide a help mechanism (icon with tooltip/popover) in the TopHeader for pages that have descriptive context.
- **FR-004**: Help icon MUST only appear when help content is defined for the page (no empty tooltips).
- **FR-005**: On tabbed pages, action buttons MUST be positioned on the same row as tabs (tabs left-aligned, actions right-aligned).
- **FR-006**: On non-tabbed pages with action buttons, buttons MUST be positioned consistently below the TopHeader area.
- **FR-007**: Layout MUST adapt gracefully on mobile viewports (existing responsive patterns should continue to work).
- **FR-008**: System MUST maintain the existing stats display functionality in the TopHeader.
- **FR-009**: Help tooltips/popovers MUST be accessible via both hover (desktop) and tap (mobile) interactions.

### Key Entities

- **PageHelpContent**: Associates a page identifier with optional descriptive help text (title and description).
- **TopHeader**: Extended to support optional help icon with associated content.
- **Page Layout**: Modified content area structure with repositioned action buttons.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All pages display exactly one page title element (zero duplicate titles across the application).
- **SC-002**: Users can access page descriptions on 100% of pages that previously had in-content descriptions via the help mechanism.
- **SC-003**: Page content area gains vertical space equivalent to the removed title row (approximately 40-60px per page).
- **SC-004**: All existing action buttons remain accessible within 2 clicks/taps from page load.
- **SC-005**: Mobile users experience no loss of functionality after layout changes.
- **SC-006**: Page layouts render correctly across common viewport widths (mobile: 320px-767px, tablet: 768px-1023px, desktop: 1024px+).

## Assumptions

- The TopHeader component is the single source of truth for page titles going forward.
- Existing stats functionality in the TopHeader remains unchanged.
- Help content will be defined per-page (or route) and can be empty/undefined for pages without descriptions.
- The shadcn/ui Tooltip or Popover component will be used for the help mechanism (consistent with existing design system).
- Action button functionality and styling remain unchanged; only positioning changes.
- Pages affected include at minimum: CollectionsPage, ConnectorsPage, AnalyticsPage, EventsPage (based on codebase exploration).

## Out of Scope

- Changes to the TopHeader stats functionality.
- Modifications to action button behavior or styling.
- Changes to tab component functionality.
- Navigation structure changes.
- New page creation.
