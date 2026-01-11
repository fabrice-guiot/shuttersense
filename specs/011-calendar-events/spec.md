# Feature Specification: Calendar of Events

**Feature Branch**: `011-calendar-events`
**Created**: 2026-01-11
**Status**: Draft
**Input**: User description: "Github issue #39: since we've just added timezone support, the application is now in the right shape to introduce the Calendar of Events feature."
**Source**: [GitHub Issue #39](https://github.com/fabrice-guiot/photo-admin/issues/39)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Events Calendar (Priority: P1)

As a photographer, I want to see my photography events on a calendar view so that I can understand my upcoming schedule at a glance and plan accordingly.

**Why this priority**: The calendar view is the core interface for this feature. Without it, no other functionality can be effectively used. It delivers immediate value by visualizing the photographer's schedule.

**Independent Test**: Can be fully tested by creating events via API and verifying they display correctly on the calendar. Delivers value by showing photographers their schedule in a visual format.

**Acceptance Scenarios**:

1. **Given** the user navigates to the Events page, **When** the calendar loads, **Then** all events for the visible month are displayed with title, date, and status indicators
2. **Given** events exist for different days, **When** viewing the calendar, **Then** each event appears on its correct date with appropriate visual distinction based on attendance status colors
3. **Given** the calendar is displayed, **When** the user clicks the previous/next month buttons, **Then** the calendar navigates and loads events for the new month
4. **Given** the user is viewing the calendar, **When** they hover over an event, **Then** a summary tooltip displays event details (title, time, location, attendance status)
5. **Given** an event is part of a multi-day series, **When** viewing the calendar, **Then** each session displays with "1/3", "2/3", "3/3" notation indicating its position in the series

---

### User Story 2 - Create and Edit Events (Priority: P1)

As a photographer, I want to create and edit events so that I can maintain an accurate record of my photography commitments.

**Why this priority**: Creating events is essential for populating the calendar. Without event creation, the calendar would be empty and unusable.

**Independent Test**: Can be tested by opening the create event dialog, filling in details, and verifying the event persists and appears on the calendar.

**Acceptance Scenarios**:

1. **Given** the user is on the Events page, **When** they click the "New Event" button, **Then** a dialog/form opens with all required event fields
2. **Given** the create event form is open, **When** the user fills in title, start date/time, end date/time, and submits, **Then** the event is created and appears on the calendar
3. **Given** the user selects an "All Day" event, **When** they submit the form, **Then** the event is created with start time at midnight and spans the full day
4. **Given** the user selects a date range spanning multiple days, **When** they submit the form, **Then** the system creates a Series of individual session Events (one per day) with shared properties
5. **Given** an event exists, **When** the user clicks on it and selects edit, **Then** they can modify all event properties and save changes
6. **Given** the user is editing an event, **When** they change the attendance status, **Then** the calendar updates to reflect the new status with appropriate visual styling (Planned=Yellow, Attended=Green, Skipped=Red)

---

### User Story 3 - Manage Event Timezone Input (Priority: P1)

As a photographer, I want to specify event times in the timezone of the event location so that I can enter times exactly as published by the organizer without manual conversion.

**Why this priority**: Events occur in various locations with different timezones. Entering times in the event's local timezone prevents errors and matches how organizers publish schedules.

**Independent Test**: Can be tested by creating an event, selecting a location in a different timezone, and verifying times can be entered in that timezone.

**Acceptance Scenarios**:

1. **Given** the user is creating an event, **When** they select a Location, **Then** the system suggests adopting that location's timezone for time input
2. **Given** a timezone is selected for input, **When** the user enters start and end times, **Then** times are displayed in that timezone during editing
3. **Given** an event was created with a specific input timezone, **When** viewing the event on the calendar, **Then** times are displayed in the user's local timezone with proper conversion

---

### User Story 4 - Track Event Logistics with Statuses (Priority: P2)

As a photographer, I want to track detailed logistics requirements and their fulfillment status so that I can ensure I'm fully prepared for each event.

**Why this priority**: Logistics tracking differentiates this from a simple calendar. It provides the operational support photographers need for event preparation.

**Independent Test**: Can be tested by creating an event with logistics requirements, progressing through each status, and verifying the UI reflects the current state.

**Acceptance Scenarios**:

1. **Given** the user is creating an event, **When** they mark "Ticket Required", **Then** a ticket status field appears with options: Not Purchased (Red), Purchased (Yellow), Ready (Green)
2. **Given** a ticket status is "Purchased" or "Ready", **When** viewing the event, **Then** a Date of Purchase field is required and displayed
3. **Given** the user marks "Time-off Required", **When** viewing the form, **Then** status options appear: Planned (Red), Booked (Yellow), Approved (Green) with Date of Booking required for Booked/Approved
4. **Given** the user marks "Travel Required", **When** viewing the form, **Then** status options appear: Planned (Red), Booked (Green) with Date of Booking required for Booked status
5. **Given** an Organizer is selected that has "Ticket Required" as default, **When** creating a new event with that Organizer, **Then** the "Ticket Required" option is pre-selected
6. **Given** a Location is selected that has "Time-off Required" or "Travel Required" as defaults, **When** creating a new event at that Location, **Then** those options are pre-selected

---

### User Story 5 - Manage Locations with Category Matching (Priority: P2)

As a photographer, I want to save and reuse known locations with ratings so that I can quickly set up events at familiar venues and remember my experience there.

**Why this priority**: Building a location database adds long-term value and enables faster event creation. Location-category matching ensures data consistency.

**Independent Test**: Can be tested by creating a known location, rating it, then creating an event that references that location.

**Acceptance Scenarios**:

1. **Given** the user is creating an event, **When** they enter a location address, **Then** the system resolves the address using an online geocoding service
2. **Given** an address is resolved, **When** the user clicks "Save as Known Location", **Then** the location is saved with its Category matching the Event's category
3. **Given** a Known Location exists, **When** creating an event in a different Category, **Then** the user cannot select that Known Location (Category must match)
4. **Given** a Known Location is selected, **When** viewing its details, **Then** the user can set/view a rating (1-5) displayed with camera icons
5. **Given** a Known Location has logistics defaults (Time-off Required, Travel Required), **When** creating an event at that location, **Then** those defaults are applied to the new event

---

### User Story 6 - Manage Organizers with Category Matching (Priority: P2)

As a photographer, I want to track event organizers so that I can manage relationships and remember which organizers require tickets by default.

**Why this priority**: Organizer tracking enables relationship management and provides smart defaults for ticket requirements.

**Independent Test**: Can be tested by creating an organizer, then creating an event that references that organizer and verifying defaults are applied.

**Acceptance Scenarios**:

1. **Given** the user is creating an event, **When** they select or create an Organizer, **Then** the Organizer's Category must match the Event's Category
2. **Given** an Organizer is created, **When** viewing its details, **Then** the user can set name, website (optional), and rating (1-5 stars)
3. **Given** an Organizer has "Ticket Required" as default, **When** creating an event with that Organizer, **Then** the event's "Ticket Required" option is pre-selected
4. **Given** an Organizer exists with a rating, **When** viewing event details with that Organizer, **Then** the rating is visible

---

### User Story 7 - View Event KPIs in TopHeader (Priority: P2)

As a photographer, I want to see at-a-glance statistics about my events in the page header so that I can quickly understand my upcoming workload and preparation status.

**Why this priority**: Follows the established TopHeader KPI pattern from the constitution, ensuring consistency with other pages in the application.

**Independent Test**: Can be tested by navigating to the Events page and verifying KPI stats display in the TopHeader area.

**Acceptance Scenarios**:

1. **Given** the user navigates to the Events page, **When** the page loads, **Then** the TopHeader displays KPIs (e.g., "Upcoming Events", "This Month", "Needs Prep")
2. **Given** events exist with various statuses, **When** viewing the TopHeader, **Then** the counts accurately reflect the current data
3. **Given** the user navigates away from Events page, **When** viewing another page, **Then** the TopHeader KPIs update to that page's context

---

### User Story 8 - Manage Performer Schedules for Events (Priority: P3)

As a photographer, I want to track which performers are scheduled to appear at events so that I can plan my shooting schedule and ensure coverage.

**Why this priority**: Performer tracking is valuable for event photographers (sports, concerts, airshows) but is not essential for basic event management.

**Independent Test**: Can be tested by creating a performer, associating them with an event, and verifying the performer schedule displays on the event detail view.

**Acceptance Scenarios**:

1. **Given** the user creates a Performer, **When** filling in details, **Then** they can enter: name, category (must match Event), website (optional), Instagram handle (optional), additional info (multiline text)
2. **Given** the user is editing an event, **When** they add a Performer, **Then** the Performer appears with status "Confirmed" by default
3. **Given** performers are associated with an event, **When** viewing the event details, **Then** all performers are listed with their attendance status
4. **Given** a performer's status changes to "Cancelled", **When** viewing the event, **Then** the performer shows with cancelled styling
5. **Given** a Performer exists in a different Category than the Event, **When** trying to add them to the Event, **Then** the system prevents the association (Category must match)

---

### User Story 9 - Categorize Events (Priority: P3)

As a photographer, I want to categorize events (Airshow, Wedding, Sports, Wildlife, etc.) so that I can filter my calendar and ensure related entities (Locations, Organizers, Performers) are properly grouped.

**Why this priority**: Categories enable organization and enforce data consistency across related entities. They are foundational but not essential for basic event creation.

**Independent Test**: Can be tested by configuring categories in Settings, then creating an event with a category.

**Acceptance Scenarios**:

1. **Given** the user accesses Settings, **When** they view the Categories section, **Then** they can add, edit, and remove event categories
2. **Given** categories are configured, **When** creating an event, **Then** the user must select a category
3. **Given** events have categories assigned, **When** viewing the calendar with a category filter, **Then** only events of that category are displayed
4. **Given** a category has an associated color/icon, **When** viewing the calendar, **Then** events display with their category's visual styling

---

### User Story 10 - Configure Event Statuses (Priority: P3)

As a photographer, I want to configure the list of available event statuses so that I can customize the workflow to match my needs.

**Why this priority**: Configurable statuses allow flexibility for different photographer workflows.

**Independent Test**: Can be tested by adding a custom status in Settings and verifying it appears as an option when editing events.

**Acceptance Scenarios**:

1. **Given** the user accesses Settings, **When** they view the Event Status section, **Then** they can configure the list of available statuses (e.g., Future, Confirmed, Completed, Cancelled)
2. **Given** custom statuses are configured, **When** creating or editing an event, **Then** all configured statuses are available for selection

---

### Edge Cases

- What happens when an event spans multiple days? System creates a Series of individual session Events, each with "x/n" display notation. All sessions share the same properties except for individual status and attendance.
- How does the system handle timezone differences? Times can be entered in the event location's timezone and are stored in UTC. Display converts to user's local timezone.
- What happens when changing an Event's category after Location/Organizer/Performers are assigned? System warns user and requires re-selection of related entities that no longer match.
- How does the system handle event deletion? Soft delete with confirmation dialog; for Series events, option to delete single session or entire series.
- What happens when trying to create overlapping events? System allows overlapping events but displays a warning about potential scheduling conflicts.
- What happens when a required logistics item remains unfulfilled close to event date? System shows warning indicators with color-coded statuses visible on calendar.

## Requirements *(mandatory)*

### Functional Requirements

#### Event Management

- **FR-001**: System MUST allow users to create events with title, description, start time, end time, and all-day flag
- **FR-002**: System MUST store all event times in UTC internally
- **FR-003**: System MUST allow users to input times in a selected timezone (defaulting to location timezone when available)
- **FR-004**: System MUST display event times in the user's local timezone on the calendar
- **FR-005**: System MUST support event statuses that are configurable in Settings (default: Future, Confirmed, Completed, Cancelled)
- **FR-006**: System MUST support attendance values: Planned (Yellow), Attended (Green), Skipped (Red)
- **FR-007**: System MUST create a Series of individual Events when user selects a multi-day date range
- **FR-008**: System MUST display Series events with "x/n" notation (e.g., "1/3", "2/3", "3/3")
- **FR-009**: System MUST share all properties across Series events except individual status and attendance
- **FR-010**: System MUST allow editing and deleting events (with option to affect single session or entire series)
- **FR-011**: System MUST use soft delete for events to preserve historical records
- **FR-012**: System MUST assign GUIDs to all events following the `evt_` prefix convention

#### Logistics Tracking

- **FR-013**: System MUST track Ticket requirement with statuses: Not Purchased (Red), Purchased (Yellow), Ready (Green)
- **FR-014**: System MUST require Date of Purchase when ticket status is Purchased or Ready
- **FR-015**: System MUST track Time-off requirement with statuses: Planned (Red), Booked (Yellow), Approved (Green)
- **FR-016**: System MUST require Date of Booking when time-off status is Booked or Approved
- **FR-017**: System MUST track Travel requirement with statuses: Planned (Red), Booked (Green)
- **FR-018**: System MUST require Date of Booking when travel status is Booked
- **FR-019**: System MUST apply default logistics requirements from Organizer (Ticket) and Location (Time-off, Travel)
- **FR-020**: System MUST allow setting a deadline date for workflow completion

#### Calendar UI

- **FR-021**: System MUST display events on a monthly calendar view
- **FR-022**: System MUST allow navigation between months
- **FR-023**: System MUST display event summary on hover/click
- **FR-024**: System MUST use semantic colors for attendance status (Planned=Yellow, Skipped=Red, Attended=Green)
- **FR-025**: System MUST follow Dark Theme compliance guidelines

#### Category System

- **FR-026**: System MUST support Category entities configurable in Settings
- **FR-027**: System MUST require a Category when creating an Event
- **FR-028**: System MUST enforce Category matching between Event and its Location
- **FR-029**: System MUST enforce Category matching between Event and its Organizer
- **FR-030**: System MUST enforce Category matching between Event and its Performers

#### Location Management

- **FR-031**: System MUST support Location entities with name, address, city, state, country, coordinates
- **FR-032**: System MUST resolve addresses using an online geocoding service
- **FR-033**: System MUST allow saving resolved locations as "Known Locations"
- **FR-034**: System MUST support Location ratings (1-5) displayed with camera icons
- **FR-035**: System MUST associate Known Locations with a Category
- **FR-036**: System MUST support default logistics settings on Locations (Time-off Required, Travel Required)

#### Organizer Management

- **FR-037**: System MUST support Organizer entities with name, website (optional), and rating (1-5 stars)
- **FR-038**: System MUST associate Organizers with a Category
- **FR-039**: System MUST support default Ticket Required setting on Organizers

#### Performer Management

- **FR-040**: System MUST support Performer entities with name, category, website (optional), Instagram handle (optional), and additional info (multiline)
- **FR-041**: System MUST support Event-Performer relationships with status: Confirmed (default), Cancelled
- **FR-042**: System MUST allow removing Performers from Events or updating their status

#### TopHeader Integration

- **FR-043**: System MUST display event KPIs in TopHeader when on Events page
- **FR-044**: System MUST provide a `/api/events/stats` endpoint for KPI data
- **FR-045**: System MUST clear TopHeader stats when navigating away from Events page

### Key Entities

- **Event**: Core calendar entry with scheduling, logistics tracking, and status. Single events or part of a Series. Identified by `evt_` GUID prefix. Must belong to a Category.
- **EventSeries**: Logical grouping linking multiple Event sessions that span multiple days. Shares properties across all member Events.
- **Location**: Physical venue where events take place. Includes address, coordinates, ratings (camera icons), and default logistics settings. Must belong to a Category. Identified by `loc_` GUID prefix.
- **Organizer**: Entity that hosts/organizes events. Includes contact information, rating (stars), and default ticket settings. Must belong to a Category. Identified by `org_` GUID prefix.
- **Category**: Classification for event types (Airshow, Wedding, Wildlife, etc.). Configurable in Settings. Enforces grouping of Events, Locations, Organizers, and Performers.
- **Performer**: Subject/participant scheduled to appear at events. Includes name, category, website, Instagram handle, and additional info. Must belong to a Category. Identified by `prf_` GUID prefix.
- **EventPerformer**: Junction entity linking performers to events with attendance status (Confirmed, Cancelled).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a new event and see it on the calendar within 5 seconds of submission
- **SC-002**: Calendar view loads and displays events for a month within 2 seconds
- **SC-003**: Users can navigate between months with sub-second response time
- **SC-004**: 95% of users can successfully create their first event without documentation
- **SC-005**: All event times display correctly converted to the user's local timezone
- **SC-006**: Multi-day event creation correctly generates a Series with "x/n" notation
- **SC-007**: TopHeader KPIs update within 1 second of page load
- **SC-008**: Logistics status colors (Red/Yellow/Green) are visible at a glance on the calendar and event details
- **SC-009**: Category matching is enforced 100% of the time when associating Locations, Organizers, and Performers with Events
- **SC-010**: System supports at least 500 events per user without performance degradation

## Assumptions

- Timezone support infrastructure (Issue #56) is complete and available
- The application will use an external geocoding service for address resolution (specific service to be determined during planning)
- Default categories will be seeded (Airshow, Wildlife, Wedding, Sports, Portrait, Concert, Motorsports) but are user-configurable
- Event status list is configurable per user/team preference
