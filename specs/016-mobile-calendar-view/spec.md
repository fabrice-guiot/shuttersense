# Feature Specification: Mobile Calendar View

**Feature Branch**: `016-mobile-calendar-view`
**Created**: 2026-01-13
**Status**: Draft
**Input**: GitHub Issue #69 - "We need a compact version of the Calendar view for Mobile"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Calendar on Mobile Device (Priority: P1)

A user opens the Events page on their mobile phone to check their upcoming events. The calendar displays in a compact format optimized for the smaller screen, where each day shows category icon badges with event counts instead of full event cards. The user can quickly scan the month to see which days have events and what types of events are scheduled.

**Why this priority**: This is the core functionality - without a compact calendar display, the feature has no value. Users on mobile devices currently see a calendar that's difficult to navigate due to cramped event cards.

**Independent Test**: Can be tested by resizing browser to mobile width (<640px) and verifying calendar cells show badge indicators instead of full event cards.

**Acceptance Scenarios**:

1. **Given** a user is viewing the Events page on a mobile device (screen width < 640px), **When** the calendar loads, **Then** each day cell displays category icon badges with event counts instead of full event card titles.

2. **Given** a day has events from multiple categories (e.g., 2 concerts, 1 sports event), **When** the user views that day in compact mode, **Then** they see separate badges for each category showing the category icon and count (e.g., music icon with "2", sports icon with "1").

3. **Given** a day has no events, **When** the user views that day in compact mode, **Then** the day cell shows only the day number with no badges.

4. **Given** the user rotates their phone to landscape orientation (width >= 640px), **When** the calendar re-renders, **Then** it switches to the standard full-card layout.

---

### User Story 2 - View Day Events from Compact Calendar (Priority: P1)

A user taps on a day number in the compact calendar to see the full list of events for that day. A popup appears showing all events with their details, allowing the user to select an event for more information.

**Why this priority**: Equal priority to P1 because without the ability to see event details, the compact badges are not actionable. This completes the core mobile experience.

**Independent Test**: Can be tested by tapping any day with events in compact mode and verifying the day detail popup appears with the complete event list.

**Acceptance Scenarios**:

1. **Given** a user is viewing the compact calendar and a day has events, **When** the user taps on the day number, **Then** a popup appears showing all events for that day with their titles, times, and category indicators.

2. **Given** the day detail popup is open, **When** the user taps on a specific event, **Then** the Event View card opens showing full event details.

3. **Given** the Event View card is open, **When** the user taps the Edit button, **Then** the Event Form dialog opens allowing event editing.

4. **Given** a user taps on a day with no events in compact mode, **When** the popup logic executes, **Then** the Create Event dialog opens with the date pre-filled (existing behavior preserved).

---

### User Story 3 - Navigate Calendar on Mobile (Priority: P2)

A user navigates between months using the calendar header controls. The navigation remains usable on mobile with appropriately sized touch targets and clear month/year indication.

**Why this priority**: Navigation is essential for practical use but is secondary to the core display and interaction patterns.

**Independent Test**: Can be tested by using previous/next month buttons and verifying smooth navigation with touch-friendly target sizes.

**Acceptance Scenarios**:

1. **Given** a user is viewing the compact calendar, **When** they tap the next month arrow, **Then** the calendar navigates to the next month and displays the compact badge view.

2. **Given** a user is viewing the compact calendar, **When** they tap the previous month arrow, **Then** the calendar navigates to the previous month.

3. **Given** the user is on mobile, **When** viewing the calendar header, **Then** navigation buttons have adequate touch target size (minimum 44x44 pixels) and the current month/year is clearly visible.

---

### Edge Cases

- What happens when a day has events from more than 5 categories? Display up to 4 category badges, then show a "+N" indicator for additional categories.
- What happens when a category has more than 99 events on a single day? Display "99+" as the count to prevent layout overflow.
- How does the system handle the transition point (exactly 640px width)? Use CSS media queries with standard breakpoints to prevent flickering during resize.
- What happens if event data is loading? Show a loading indicator on the calendar while maintaining the compact grid structure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect mobile viewport (width < 640px) and render the compact calendar layout automatically.
- **FR-002**: System MUST display category icon badges with event counts for each day in compact mode, grouped by event category.
- **FR-003**: System MUST maintain clickable day numbers that open the day detail popup with the full event list.
- **FR-004**: System MUST preserve all existing dialog flows (Day Detail → Event View → Event Edit) in mobile view.
- **FR-005**: System MUST switch to the standard full-card calendar layout when viewport width reaches 640px or greater.
- **FR-006**: System MUST ensure the compact calendar grid maintains the standard 7-column layout (Sunday through Saturday).
- **FR-007**: System MUST reduce the minimum cell height in compact mode to allow more days to be visible on screen.
- **FR-008**: System MUST display the category's assigned icon and color in each badge.
- **FR-009**: System MUST show a numeric count next to each category icon indicating how many events of that category exist on that day.
- **FR-010**: System MUST preserve keyboard navigation and screen reader accessibility in compact mode.

### Key Entities

- **Category Badge**: A compact visual element showing a category icon and event count for a specific day, replacing the full event card display in mobile view.
- **Compact Calendar Cell**: A reduced-height day cell containing the day number and zero or more category badges, optimized for mobile viewport.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view a complete month on a mobile screen without horizontal scrolling.
- **SC-002**: Users can identify which days have events and their categories within 2 seconds of viewing the calendar.
- **SC-003**: Users can access full event details within 2 taps from the compact calendar view (tap day → tap event).
- **SC-004**: All existing calendar functionality (create, view, edit, delete events) remains accessible on mobile devices.
- **SC-005**: Calendar cells in compact mode display at least 50% smaller height than desktop mode while remaining touch-friendly.
- **SC-006**: The transition between compact and standard layouts occurs smoothly without page reload or data loss.

## Assumptions

- The existing dialog components (Day Detail, Event View, Event Form) are already sufficiently responsive for mobile use, as stated in the issue.
- The standard Tailwind CSS breakpoint of 640px (`sm:`) is appropriate for distinguishing mobile from tablet/desktop.
- Category icons are already available in the system and displayed elsewhere in the application.
- Users expect to see a summary view on mobile rather than attempting to fit full event details into small cells.
