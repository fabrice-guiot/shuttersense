# Feature Specification: User Timezone Display

**Feature Branch**: `010-user-timezone-display`
**Created**: 2026-01-11
**Status**: Draft
**Input**: User description: "Github issue #56, based on the requirements documented in docs/prd/008-user-timezone-display.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Timestamps in Local Timezone (Priority: P1)

As a photo collection manager, I want to see all timestamps displayed in my local timezone so that I can easily understand when events occurred without mental timezone conversion.

**Why this priority**: This is the core value proposition of the feature. Without local timezone display, users must mentally convert UTC timestamps, which is error-prone and frustrating.

**Independent Test**: Can be fully tested by viewing any page with timestamps (e.g., Collections list, Connectors list) and verifying times display in the user's local timezone with a human-readable format like "Jan 7, 2026, 3:45 PM".

**Acceptance Scenarios**:

1. **Given** I am viewing the Connectors list page, **When** a connector shows a "last validated" timestamp, **Then** the timestamp displays in my local timezone with format "Jan 7, 2026, 3:45 PM" (or equivalent locale-appropriate format)
2. **Given** I am in the EST timezone (UTC-5), **When** I view a timestamp stored as "2026-01-07T15:45:00" (UTC), **Then** I see "Jan 7, 2026, 10:45 AM" displayed
3. **Given** I am viewing a Collection details page, **When** looking at "created_at" and "updated_at" fields, **Then** both timestamps display in my local timezone consistently

---

### User Story 2 - View Relative Time for Recent Events (Priority: P1)

As a photo collection manager, I want to see recent timestamps as relative times (e.g., "2 hours ago", "yesterday") so that I can quickly understand how recent an event was without parsing exact dates.

**Why this priority**: Relative times significantly improve user experience for recent events, which are the most commonly viewed timestamps.

**Independent Test**: Can be tested by creating or updating an item and verifying the timestamp shows as "just now" or "X minutes ago" rather than an absolute date.

**Acceptance Scenarios**:

1. **Given** a connector was last validated 30 minutes ago, **When** I view the connector list, **Then** I see "30 minutes ago" instead of the absolute timestamp
2. **Given** a collection was created yesterday, **When** I view the collection details, **Then** I see "yesterday" or "1 day ago" as the relative time
3. **Given** a connector was last validated 2 weeks ago, **When** I view the connector list, **Then** the system displays an absolute date rather than relative time

---

### User Story 3 - Graceful Handling of Missing Dates (Priority: P2)

As a user, I want timestamps that have never been set to display as "Never" so that I understand no value exists rather than seeing confusing empty or error states.

**Why this priority**: Proper null handling ensures a polished user experience and prevents confusion about missing data.

**Independent Test**: Can be tested by viewing a connector that has never been validated and confirming "Never" displays instead of a blank or error.

**Acceptance Scenarios**:

1. **Given** a connector has never been validated (last_validated is null), **When** I view the connector list, **Then** I see "Never" for the last validated field
2. **Given** a date field contains an invalid/malformed value, **When** the system attempts to display it, **Then** the system gracefully shows a fallback text without crashing

---

### Edge Cases

- What happens when the browser's Intl API is unavailable? The system falls back to basic `toLocaleString()` formatting.
- How does the system handle invalid ISO 8601 date strings? The system displays a fallback text (e.g., "Invalid date") rather than crashing.
- What happens when a user crosses timezone boundaries (e.g., traveling)? The display automatically updates to reflect the device's current timezone on page refresh.
- How are dates at year boundaries displayed? Dates from a different year show the full year; dates from the current year may omit the year for brevity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a centralized date formatting utility that all components use for timestamp display
- **FR-002**: System MUST display all timestamps in the user's device/browser timezone
- **FR-003**: System MUST support absolute date/time formatting with a default format of medium date with short time (e.g., "Jan 7, 2026, 3:45 PM")
- **FR-004**: System MUST support relative time formatting that displays human-friendly strings like "2 hours ago", "yesterday", "3 days ago"
- **FR-005**: System MUST handle null and undefined date values by displaying "Never" or similar appropriate text
- **FR-006**: System MUST use the browser's native Intl API for locale-aware formatting
- **FR-007**: System MUST replace all existing inline date formatting functions with the centralized utility
- **FR-008**: System MUST provide graceful fallback to `toLocaleString()` if Intl APIs are unavailable

### Non-Functional Requirements

- **NFR-001**: Date formatting operations MUST NOT cause visible UI lag or performance degradation
- **NFR-002**: The solution MUST NOT require any external date libraries (use native browser APIs only)
- **NFR-003**: The solution MUST support all modern browsers (Chrome 71+, Firefox 65+, Safari 14+, Edge 79+)
- **NFR-004**: All formatting functions MUST have unit test coverage of at least 90%

### Key Entities

- **Timestamp Display**: Represents any date/time value shown in the UI; may be displayed as absolute (formatted date string) or relative ("X time ago") depending on context
- **Date Formatting Utility**: Centralized module providing consistent formatting functions used across all frontend components

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of timestamp displays in the application use the centralized date formatting utility
- **SC-002**: Zero inline date formatting functions remain in component files
- **SC-003**: Date formatting utility has at least 90% unit test coverage
- **SC-004**: Timestamps display correctly when tested in at least 3 different browser locales (e.g., en-US, fr-FR, de-DE)
- **SC-005**: Users in different timezones see the same UTC timestamp converted correctly to their respective local times
- **SC-006**: Null/undefined dates consistently display as "Never" across all components

## Assumptions

- The backend will continue to store and return timestamps in UTC format (ISO 8601)
- No backend changes are required for this feature
- Users' browsers have accurate timezone settings
- The application targets modern browsers that support Intl.DateTimeFormat and Intl.RelativeTimeFormat
- Components may choose between absolute and relative time display based on their specific context and UX needs
- Relative time thresholds (when to switch from relative to absolute) will use reasonable defaults: relative for times within approximately 7-14 days, absolute for older dates

## Dependencies

- Existing frontend components that display timestamps must be identified and migrated
- The design system may need guidelines added for when to use relative vs. absolute time display

## Out of Scope

- User timezone preferences stored in user accounts (requires user management system)
- Manual timezone selector UI
- Backend modifications to timestamp storage or API responses
- Server-side rendering timezone handling
- Timezone indicator display (e.g., showing "EST" suffix)
