# Feature Specification: Event Deadline Calendar Display

**Feature Branch**: `018-event-deadline-calendar`
**Created**: 2026-01-14
**Status**: Draft
**Input**: GitHub Issue #68 - Make Event Deadline appear in the Calendar view

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Event Deadlines in Calendar (Priority: P1)

As a photographer, I want to see post-event processing deadlines displayed in my calendar view so that I can track when images must be delivered to clients or submitted to competitions.

**Primary use case**: Deadlines track when post-event image processing must be completed. Examples include:
- Commercial engagements where the customer expects image delivery by a certain date/time
- Photography competitions with submission deadlines for participation
- Editorial assignments with publication deadlines

In the typical workflow, the deadline date **follows** the event date in the calendar (event happens first, then images are processed and delivered by the deadline).

When an Event Series has a deadline date set, a deadline entry automatically appears in the calendar on that date. This allows photographers to see at a glance when deliverables are due.

**Secondary use case**: While the primary use case is post-event deadlines, the system also supports pre-event deadlines (e.g., preparation tasks) if users choose to use it that way.

**Why this priority**: This is the core value proposition - making deadlines visible in the calendar is the primary user need. Without this, users have no way to see delivery/submission deadlines alongside their events.

**Independent Test**: Can be fully tested by creating an Event Series with a deadline date and verifying the deadline appears as a distinct entry in the calendar on the deadline date.

**Acceptance Scenarios**:

1. **Given** an Event Series with an event on March 1 and a deadline date of March 15, **When** I view the March calendar, **Then** I see the event on March 1 and a deadline entry on March 15 displayed as "[Deadline] Event Series Name" with a red color and clock-alert icon
2. **Given** an Event Series with a deadline date, **When** the deadline entry appears in the calendar, **Then** it shows the Event Series organizer but has no location or performers displayed
3. **Given** an Event Series where the deadline has a specific time set (e.g., competition closes at 11:59 PM), **When** I view the deadline entry, **Then** the entry shows that time as both start and end time (making it a point-in-time deadline)
4. **Given** a commercial photography Event Series, **When** I set the deadline to 2 weeks after the event date, **Then** the deadline entry appears on the calendar 2 weeks after the event, clearly showing when client delivery is due

---

### User Story 2 - Automatic Deadline Entry Management (Priority: P1)

As a system user, I expect deadline entries to be automatically synchronized with their parent Event Series, so I don't have to manually manage duplicate entries.

When I create, update, or delete deadline information on an Event Series, the corresponding deadline calendar entry updates automatically without any additional action from me.

**Why this priority**: Critical for data integrity. Users should not be burdened with manually maintaining deadline entries, and the system must ensure consistency between Event Series deadline settings and their calendar representation.

**Independent Test**: Can be fully tested by modifying deadline information on an Event Series and verifying the deadline entry updates accordingly without manual intervention.

**Acceptance Scenarios**:

1. **Given** an Event Series without a deadline, **When** I add a deadline date to the Event Series, **Then** a deadline entry automatically appears in the calendar on that date
2. **Given** an Event Series with a deadline, **When** I change the deadline date, **Then** the deadline calendar entry automatically moves to the new date
3. **Given** an Event Series with a deadline, **When** I remove the deadline date, **Then** the deadline calendar entry automatically disappears from the calendar
4. **Given** an Event Series with a deadline, **When** I delete the entire Event Series, **Then** the deadline entry is also removed from the calendar

---

### User Story 3 - Protected Deadline Entries (Priority: P2)

As a system administrator, I want deadline entries to be protected from direct modification so that they always accurately reflect the Event Series deadline information.

Deadline entries are read-only - they cannot be edited, deleted, or created independently. All changes must flow through the parent Event Series.

**Why this priority**: Ensures data integrity and prevents confusion. Users should modify deadlines at the source (Event Series), not on derived entries.

**Independent Test**: Can be fully tested by attempting to edit or delete a deadline entry directly and verifying the operation is prevented.

**Acceptance Scenarios**:

1. **Given** a deadline entry in the calendar, **When** I try to open it for editing, **Then** I see a read-only view that explains this is a deadline and points to the parent Event Series for changes
2. **Given** a deadline entry, **When** I try to delete it directly through the UI, **Then** the delete option is not available or is disabled
3. **Given** a deadline entry, **When** API requests attempt to modify or delete it, **Then** the system returns an appropriate error indicating the entry cannot be modified directly

---

### User Story 4 - Deadline Visibility in Events API (Priority: P2)

As a developer consuming the Events API, I expect deadline entries to appear in the standard events list so that calendar views and integrations automatically include them.

Deadline entries appear in the Events API response alongside regular events, properly typed and identifiable as deadline entries.

**Why this priority**: Essential for proper calendar rendering and future integrations. The API is the contract that ensures deadline visibility across all views.

**Independent Test**: Can be fully tested by calling the Events API for a date range containing a deadline and verifying the deadline entry appears in the response with appropriate typing.

**Acceptance Scenarios**:

1. **Given** a date range containing an Event Series deadline, **When** I query the Events API for that range, **Then** the deadline entry appears in the results
2. **Given** a deadline entry returned by the API, **When** I inspect its data, **Then** it includes a type or marker indicating it is a deadline entry (not a regular event)
3. **Given** a deadline entry, **When** I view its details, **Then** it references its parent Event Series GUID

---

### Edge Cases

- Can an Event Series have multiple deadlines? No. Deadline is a Series-level property (like location and organizer). There is exactly one deadline per Series, and it applies to all Events in that Series. The single deadline entry appears once on its date, representing the deadline for the entire series.
- What happens when the deadline date is in the past? The deadline entry still appears in the calendar for historical reference (e.g., to see when a delivery was due). Past deadlines may be visually indicated as expired. This is the normal state after successful delivery - the event happened, images were processed, and the deadline passed.
- What happens when an Event Series deadline date matches an event date in the same series? Both entries appear on that date - the regular event and the deadline entry - distinguishable by their styling and type.
- Can the deadline date be before the event date? Yes, the system does not enforce any relationship between event dates and deadline dates. While the primary use case has deadlines after events (post-event processing), users may set deadlines before events for preparation tasks if they choose.
- How does the system handle bulk operations? When multiple Event Series are updated, all corresponding deadline entries are synchronized accordingly.
- What happens if an Event has a deadline_date field set (legacy)? Individual event deadlines are separate from Event Series deadlines. This feature focuses on Event Series-level deadlines only. Individual event deadline_date fields remain unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display Event Series deadlines as distinct entries in the calendar view on their respective deadline dates
- **FR-002**: Deadline entries MUST be displayed with the format "[Deadline] {Event Series Name}" as their title
- **FR-003**: Deadline entries MUST use a red color scheme to distinguish them from regular events
- **FR-004**: Deadline entries MUST display the ClockAlert icon from Lucide icons library
- **FR-005**: Deadline entries MUST inherit the organizer from their parent Event Series
- **FR-006**: Deadline entries MUST NOT display location information (shown as empty/none)
- **FR-007**: Deadline entries MUST NOT display performer information
- **FR-008**: When an Event Series has a deadline time specified, the deadline entry MUST use that time for both start and end time
- **FR-009**: Deadline entries MUST be stored as separate event records in the system for proper calendar API integration
- **FR-010**: System MUST automatically create a deadline entry when a deadline date is added to an Event Series
- **FR-011**: System MUST automatically update the deadline entry when the Event Series deadline date or time changes
- **FR-012**: System MUST automatically delete the deadline entry when the Event Series deadline is removed
- **FR-013**: System MUST automatically delete deadline entries when their parent Event Series is deleted
- **FR-014**: Deadline entries MUST NOT be directly editable through the user interface
- **FR-015**: Deadline entries MUST NOT be directly deletable through the user interface
- **FR-016**: Deadline entries MUST NOT be directly modifiable through the API (create, update, delete endpoints must reject operations on deadline entries)
- **FR-017**: Deadline entries MUST be retrievable through the standard Events API list and detail endpoints
- **FR-018**: Deadline entries MUST include a marker or type field indicating they are deadline entries
- **FR-019**: Deadline entries MUST include a reference to their parent Event Series
- **FR-020**: Event Series MUST have a deadline_date field to store the deadline date
- **FR-021**: Event Series MUST have a deadline_time field to store the optional deadline time

### Key Entities

- **Event Series**: Extended to include deadline_date and deadline_time fields. These are Series-level properties (like location and organizer) - there is exactly one deadline per Series that applies to all Events in that Series. The deadline typically represents when post-event deliverables are due (client delivery, competition submission). When set, triggers automatic creation/management of associated deadline entry.
- **Deadline Entry**: A specialized event record representing an Event Series deadline. Distinguished by a type marker, inherits limited properties from parent Event Series (title prefix, organizer), and is protected from direct modification. Stored as an Event record with special constraints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Event Series with deadline dates have corresponding deadline entries visible in the calendar
- **SC-002**: Users can identify deadline entries within 2 seconds by their distinct visual styling (red color, clock icon, "[Deadline]" prefix)
- **SC-003**: Deadline entry synchronization completes within 1 second of Event Series deadline modification
- **SC-004**: Zero data inconsistencies between Event Series deadlines and their calendar representations
- **SC-005**: 100% of API modification attempts on deadline entries are correctly rejected with appropriate error messages
- **SC-006**: Users can navigate from a deadline entry to its parent Event Series within 2 clicks
- **SC-007**: Primary workflow supported: Users can create an Event Series, set a deadline date after the event date, and see both the event and deadline displayed correctly in chronological order on the calendar

## Assumptions

- The Lucide ClockAlert icon is available and appropriate for the deadline visual indicator
- Red is an acceptable and accessible color choice for deadline entries (will follow existing design system color tokens)
- Users are familiar with the concept of "[Deadline]" prefix notation from similar applications
- Deadline is a Series-level property (confirmed): one deadline per Series applies to all Events in that Series
- Primary use case (confirmed): Deadlines represent post-event processing deliverables (client delivery, competition submission), so deadlines typically follow events in the calendar
- The existing Event model structure can accommodate deadline entries with a type discriminator
- Deadline entries appearing in the Events API will not break existing integrations (the type field allows filtering)
