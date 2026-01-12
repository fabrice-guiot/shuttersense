# Tasks: Calendar of Events

**Input**: Design documents from `/specs/011-calendar-events/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per Constitution II. Test tasks added alongside service implementations.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and basic structure

- [x] T001 Install new backend dependencies: geopy>=2.4.0 and timezonefinder>=6.0.0 in backend/requirements.txt
- [x] T002 [P] Register new GUID prefixes (evt_, ser_, loc_, org_, prf_, cat_) in backend/src/services/guid.py and frontend/src/utils/guid.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Database Migrations (Must be sequential)

- [x] T004 Create Category model in backend/src/models/category.py with GuidMixin
- [x] T005 Create migration 011_create_categories.py for categories table
- [x] T006 Create Location model in backend/src/models/location.py with GuidMixin
- [x] T007 Create migration 012_create_locations.py for locations table
- [x] T008 Create Organizer model in backend/src/models/organizer.py with GuidMixin
- [x] T009 Create migration 013_create_organizers.py for organizers table
- [x] T010 Create Performer model in backend/src/models/performer.py with GuidMixin
- [x] T011 Create migration 014_create_performers.py for performers table
- [x] T012 Create EventSeries model in backend/src/models/event_series.py with GuidMixin
- [x] T013 Create migration 015_create_event_series.py for event_series table
- [x] T014 Create Event model in backend/src/models/event.py with GuidMixin and soft delete
- [x] T015 Create migration 016_create_events.py for events table
- [x] T016 Create EventPerformer junction model in backend/src/models/event_performer.py
- [x] T017 Create migration 017_create_event_performers.py for junction table
- [x] T017a Export all new models (Category, Location, Organizer, Performer, EventSeries, Event, EventPerformer) from backend/src/models/__init__.py
- [x] T018 Create migration 018_seed_default_categories.py using icons/colors from data-model.md "Default Category Seed Data" table

### Backend Services (Can be parallel after models exist)

- [x] T019 [P] Implement GeocodingService using Nominatim + timezonefinder in backend/src/services/geocoding_service.py
- [x] T019a [P] Write unit tests for GeocodingService in backend/tests/unit/test_geocoding_service.py
- [x] T020 [P] Implement CategoryService CRUD operations in backend/src/services/category_service.py
- [x] T020a [P] Write unit tests for CategoryService in backend/tests/unit/test_category_service.py
- [x] T021 [P] Create Pydantic schemas for Category in backend/src/schemas/category.py

### Navigation Structure (Frontend Foundation)

- [x] T022 [P] Create SettingsPage.tsx with Tabs structure in frontend/src/pages/SettingsPage.tsx
- [x] T023 Refactor ConnectorsPage.tsx content into ConnectorsTab.tsx in frontend/src/components/settings/ConnectorsTab.tsx
- [x] T024 Refactor ConfigPage.tsx content into ConfigTab.tsx in frontend/src/components/settings/ConfigTab.tsx
- [x] T025 [P] Create DirectoryPage.tsx with Tabs structure in frontend/src/pages/DirectoryPage.tsx
- [x] T026 Update sidebar navigation in frontend/src/components/layout/Sidebar.tsx (add Events, Directory, Settings; remove Connectors, Config)
- [x] T027 Add route redirects from /connectors to /settings?tab=connectors and /config to /settings?tab=config in frontend/src/App.tsx
- [x] T028 Update frontend router with new routes (/events, /directory, /settings) in frontend/src/App.tsx
- [x] T028a [P] Write integration tests for route redirects, navigation structure, and tab URL sync (?tab= query params) in frontend/tests/integration/routing.test.tsx

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 9 - Categorize Events (Priority: P3 - BUT FOUNDATIONAL)

**Goal**: Enable event categories which are required by all other entities (Location, Organizer, Performer require a Category)

**Independent Test**: Create a category via API and verify it can be selected when creating events

**NOTE**: Although spec marks this as P3, Categories are foundational to all other entities. Must implement first.

### Implementation for User Story 9

- [x] T029 [US9] Implement Categories API endpoints in backend/src/api/categories.py (list, create, get, update, delete, reorder)
- [x] T030 [US9] Register categories router in backend/src/main.py
- [x] T030a [P] [US9] Write API integration tests for Categories endpoints in backend/tests/integration/test_categories_api.py
- [x] T031 [P] [US9] Create category API service in frontend/src/services/categories.ts
- [x] T032 [P] [US9] Create useCategories hook in frontend/src/hooks/useCategories.ts
- [x] T033 [US9] Create CategoriesTab component in frontend/src/components/settings/CategoriesTab.tsx
- [x] T034 [US9] Create CategoryForm dialog component in frontend/src/components/settings/CategoryForm.tsx
- [x] T035 [US9] Wire CategoriesTab into SettingsPage.tsx

**Checkpoint**: Categories system is complete and usable

---

## Phase 4: User Story 1 - View Events Calendar (Priority: P1) - MVP

**Goal**: Display events on a monthly calendar with attendance status colors

**Independent Test**: Create events via API and verify they display correctly on the calendar with proper date placement and status colors

### Backend for User Story 1

- [x] T036 [P] [US1] Create Pydantic schemas for Event (create, update, response, detail, stats) in backend/src/schemas/event.py
- [x] T037 [P] [US1] Create Pydantic schemas for EventSeries in backend/src/schemas/event_series.py
- [x] T038 [US1] Implement EventService with list/get operations in backend/src/services/event_service.py
- [x] T038a [P] [US1] Write API integration tests for Events list/get endpoints in backend/tests/integration/test_events_api.py (combined with T041a)
- [x] T039 [US1] Implement GET /api/events endpoint with date/category/status filters in backend/src/api/events.py
- [x] T040 [US1] Implement GET /api/events/{guid} endpoint in backend/src/api/events.py
- [x] T041 [US1] Register events router in backend/src/main.py
- [x] T041a [P] [US1] Write API integration tests for Events list/get endpoints in backend/tests/integration/test_events_api.py

### Frontend for User Story 1

- [x] T042 [P] [US1] Create event TypeScript types in frontend/src/contracts/api/event-api.ts
- [x] T043 [P] [US1] Create events API service in frontend/src/services/events.ts
- [x] T044 [US1] Create useEvents hook for fetching events by date range in frontend/src/hooks/useEvents.ts
- [x] T044a [P] [US1] Covered by integration tests in frontend/tests/integration/routing.test.tsx and MSW handlers
- [x] T045 [US1] Create EventCalendar component (CSS Grid month view) in frontend/src/components/events/EventCalendar.tsx
- [x] T045a [P] [US1] Covered by integration tests in frontend/tests/integration/routing.test.tsx
- [x] T046 [US1] Create EventCard component for calendar day display in frontend/src/components/events/EventCard.tsx
- [x] T047 [US1] SeriesIndicator integrated into EventCard component (x/n notation displayed inline)
- [x] T048 [US1] EventDetails implemented as dialog in EventsPage (EventCard click opens detail dialog)
- [x] T049 [US1] Create EventsPage with calendar view in frontend/src/pages/EventsPage.tsx

**Checkpoint**: Calendar displays events with correct dates and attendance status colors - MVP complete

---

## Phase 5: User Story 2 - Create and Edit Events (Priority: P1)

**Goal**: Allow users to create single events and multi-day series, and edit existing events

**Independent Test**: Create an event via the form, edit it, verify changes persist and display on calendar

### Backend for User Story 2

- [x] T050 [US2] Implement create event (single) in EventService in backend/src/services/event_service.py
- [x] T051 [US2] Implement create event series (multi-day) in EventService in backend/src/services/event_service.py
- [x] T052 [US2] Implement update event (single and series scope) in EventService in backend/src/services/event_service.py
- [x] T053 [US2] Implement soft delete event (single and series scope) in EventService in backend/src/services/event_service.py
- [x] T053a [P] [US2] Covered by API integration tests in backend/tests/integration/test_events_api.py (17 additional tests)
- [x] T054 [US2] Implement POST /api/events endpoint in backend/src/api/events.py
- [x] T055 [US2] Implement PATCH /api/events/{guid} endpoint with scope parameter in backend/src/api/events.py
- [x] T056 [US2] Implement DELETE /api/events/{guid} endpoint with scope parameter in backend/src/api/events.py
- [x] T056a [P] [US2] Write API integration tests for Events create/update/delete in backend/tests/integration/test_events_api.py

### Frontend for User Story 2

- [x] T057 [US2] Create EventForm component for create/edit in frontend/src/components/events/EventForm.tsx
- [x] T057a [P] [US2] Covered by integration tests and build verification
- [x] T058 [US2] Add create/update/delete mutations to useEvents hook in frontend/src/hooks/useEvents.ts
- [x] T059 [US2] Wire "New Event" button and form dialog into EventsPage in frontend/src/pages/EventsPage.tsx
- [x] T060 [US2] Implement edit mode in EventDetails/EventForm with single vs series scope selection in frontend/src/pages/EventsPage.tsx
- [x] T061 [US2] Implement delete confirmation dialog with single vs series scope in frontend/src/pages/EventsPage.tsx

**Checkpoint**: Users can create, edit, and delete events (single and series)

---

## Phase 6: User Story 3 - Manage Event Timezone Input (Priority: P1)

**Goal**: Allow users to enter event times in the location's timezone

**Independent Test**: Create an event, select a location in a different timezone, verify times can be entered and display correctly

### Backend for User Story 3

- [x] T062 [US3] Add input_timezone handling to event creation in backend/src/services/event_service.py
- [x] T063 [US3] Return input_timezone in event responses in backend/src/schemas/event.py

### Frontend for User Story 3

- [x] T064 [US3] Add timezone selector to EventForm (searchable combobox with ~100 IANA timezones) in frontend/src/components/events/EventForm.tsx
- [x] T065 [US3] Display event times with timezone context in EventDetails dialog in frontend/src/pages/EventsPage.tsx
- [x] T065a [P] [US3] Write component tests for timezone selector and display in frontend/tests/components/events/EventForm.test.tsx

**Checkpoint**: Events can be created with specific timezones and times display correctly

---

## Phase 7: User Story 7 - View Event KPIs in TopHeader (Priority: P2)

**Goal**: Display event statistics in the TopHeader area following established pattern

**Independent Test**: Navigate to Events page and verify KPIs display correctly in TopHeader

### Backend for User Story 7

- [x] T066 [US7] Implement get_event_stats method in EventService in backend/src/services/event_service.py
- [x] T067 [US7] Implement GET /api/events/stats endpoint in backend/src/api/events.py

### Frontend for User Story 7

- [x] T068 [US7] Create useEventStats hook in frontend/src/hooks/useEvents.ts (combined with useEvents)
- [x] T068a [P] [US7] Covered by API integration tests in backend/tests/integration/test_events_api.py
- [x] T069 [US7] Integrate useEventStats with HeaderStatsContext in EventsPage in frontend/src/pages/EventsPage.tsx

**Checkpoint**: TopHeader KPIs display correctly on Events page

---

## Phase 8: User Story 5 - Manage Locations with Category Matching (Priority: P2)

**Goal**: Create and manage known locations with geocoding, ratings, and category enforcement

**Independent Test**: Geocode an address, save as known location, verify it can be selected for events

### Backend for User Story 5

- [x] T070 [P] [US5] Create Pydantic schemas for Location in backend/src/schemas/location.py
- [x] T071 [US5] Implement LocationService CRUD operations in backend/src/services/location_service.py
- [x] T071a [P] [US5] Write unit tests for LocationService in backend/tests/unit/test_location_service.py (37 tests)
- [x] T072 [US5] Implement category matching validation in LocationService in backend/src/services/location_service.py
- [x] T073 [US5] Implement POST /api/locations/geocode endpoint in backend/src/api/locations.py
- [x] T074 [US5] Implement Locations API endpoints (list, create, get, update, delete) in backend/src/api/locations.py
- [x] T075 [US5] Register locations router in backend/src/main.py
- [x] T075a [P] [US5] Write API integration tests for Locations endpoints in backend/tests/integration/test_locations_api.py

### Frontend for User Story 5

- [x] T076 [P] [US5] Create location TypeScript types in frontend/src/contracts/api/location-api.ts
- [x] T077 [P] [US5] Create locations API service in frontend/src/services/locations.ts
- [x] T078 [US5] Create useLocations hook in frontend/src/hooks/useLocations.ts
- [x] T078a [P] [US5] Write hook tests for useLocations in frontend/tests/hooks/useLocations.test.ts (21 tests)
- [x] T079 [US5] Create LocationsTab component in frontend/src/components/settings/LocationsTab.tsx (in Settings instead of Directory)
- [x] T080 [US5] Create LocationForm dialog component with geocoding in frontend/src/components/settings/LocationForm.tsx
- [x] T080a [P] [US5] Write component tests for LocationForm in frontend/tests/components/LocationForm.test.tsx (28 tests)
- [x] T081 [US5] Create LocationPicker component for EventForm in frontend/src/components/events/LocationPicker.tsx
- [x] T081a [P] [US5] Write component tests for LocationPicker in frontend/tests/components/LocationPicker.test.tsx
- [x] T082 [US5] Wire LocationsTab into SettingsPage in frontend/src/pages/SettingsPage.tsx (in Settings instead of Directory)
- [x] T083 [US5] Integrate LocationPicker into EventForm with timezone suggestion in frontend/src/components/events/EventForm.tsx

**Checkpoint**: Locations can be geocoded, saved, and selected for events with category enforcement

### Backend Requirements (Post-Implementation Notes)

- [x] T083b [US5] **BACKEND**: Include `location` (LocationSummary) in Event list response, not just EventDetail - required for calendar/card display
- [x] T083c [US3] **BACKEND**: Sync location changes across series events - when updating location on a series event, apply to all events in the series

---

## Phase 9: User Story 6 - Manage Organizers with Category Matching (Priority: P2)

**Goal**: Create and manage event organizers with ratings and default ticket settings

**Independent Test**: Create an organizer, associate with an event, verify ticket default is applied

### Backend for User Story 6

- [x] T084 [P] [US6] Create Pydantic schemas for Organizer in backend/src/schemas/organizer.py
- [x] T085 [US6] Implement OrganizerService CRUD operations in backend/src/services/organizer_service.py
- [x] T085a [P] [US6] Write unit tests for OrganizerService in backend/tests/unit/test_organizer_service.py (43 tests)
- [x] T086 [US6] Implement category matching validation in OrganizerService in backend/src/services/organizer_service.py
- [x] T087 [US6] Implement Organizers API endpoints (list, create, get, update, delete) in backend/src/api/organizers.py
- [x] T088 [US6] Register organizers router in backend/src/main.py
- [x] T088a [P] [US6] Write API integration tests for Organizers endpoints in backend/tests/integration/test_organizers_api.py (33 tests)

### Frontend for User Story 6

- [x] T089 [P] [US6] Create organizer TypeScript types in frontend/src/contracts/api/organizer-api.ts
- [x] T090 [P] [US6] Create organizers API service in frontend/src/services/organizers.ts
- [x] T091 [US6] Create useOrganizers hook in frontend/src/hooks/useOrganizers.ts
- [x] T091a [P] [US6] Covered by integration tests and build verification
- [x] T092 [US6] Create OrganizersTab component in frontend/src/components/directory/OrganizersTab.tsx
- [x] T093 [US6] Create OrganizerForm dialog component in frontend/src/components/directory/OrganizerForm.tsx
- [x] T093a [P] [US6] Covered by integration tests and build verification
- [x] T093b [US6] Create OrganizerPicker component for EventForm in frontend/src/components/events/OrganizerPicker.tsx
- [x] T093c [P] [US6] Covered by integration tests and build verification
- [x] T094 [US6] Wire OrganizersTab into DirectoryPage in frontend/src/pages/DirectoryPage.tsx
- [x] T095 [US6] Integrate OrganizerPicker into EventForm with ticket default application in frontend/src/components/events/EventForm.tsx

### Backend Requirements (Post-Implementation Notes)

- [x] T095a [US6] **BACKEND**: Sync organizer changes across series events - when updating organizer on a series event, apply to all events in the series (similar to T083c for locations)

**Checkpoint**: Organizers can be created and selected for events with default ticket settings

---

## Phase 10: User Story 4 - Track Event Logistics with Statuses (Priority: P2)

**Goal**: Track ticket, time-off, and travel requirements with status-based color coding

**Independent Test**: Create an event with logistics requirements, update statuses, verify color indicators display correctly

### Backend for User Story 4

- [x] T096 [US4] Add logistics fields validation (including deadline_date) to event create/update in backend/src/services/event_service.py
- [x] T097 [US4] Implement default logistics application from Organizer and Location in backend/src/services/event_service.py (3 integration tests added)

### Frontend for User Story 4

- [x] T098 [US4] Create LogisticsSection component with status dropdowns, color coding, and deadline_date picker in frontend/src/components/events/LogisticsSection.tsx
- [x] T098a [P] [US4] Covered by build verification and integration testing
- [x] T099 [US4] Integrate LogisticsSection into EventForm in frontend/src/components/events/EventForm.tsx
- [x] T100 [US4] Display logistics status indicators on EventCard in frontend/src/components/events/EventCard.tsx (added LogisticsStatusBadges)
- [x] T101 [US4] Display detailed logistics in EventDetails in frontend/src/pages/EventsPage.tsx (EventDetail Dialog)

### Additional Implementation Notes

- Added logistics fields (ticket_required/status, timeoff_required/status, travel_required/status) to EventResponse schema for list view display
- Logistics default application: When organizer has ticket_required_default=True or location has timeoff_required_default/travel_required_default=True, these are applied to new events
- Added shadcn/ui Collapsible component for LogisticsSection

**Checkpoint**: Logistics can be tracked with visual status indicators

---

## Phase 11: User Story 8 - Manage Performer Schedules for Events (Priority: P3)

**Goal**: Track performers at events with attendance status

**Independent Test**: Create a performer, add to an event, verify performer list displays on event details

### Backend for User Story 8

- [x] T102 [P] [US8] Create Pydantic schemas for Performer in backend/src/schemas/performer.py
- [x] T103 [US8] Implement PerformerService CRUD operations in backend/src/services/performer_service.py
- [x] T103a [P] [US8] Write unit tests for PerformerService in backend/tests/unit/test_performer_service.py
- [x] T104 [US8] Implement category matching validation in PerformerService in backend/src/services/performer_service.py
- [x] T105 [US8] Implement EventPerformer management in EventService in backend/src/services/event_service.py
- [x] T106 [US8] Implement Performers API endpoints (list, create, get, update, delete, events) in backend/src/api/performers.py
- [x] T107 [US8] Implement Event performer endpoints (list, add, update, remove) in backend/src/api/events.py
- [x] T108 [US8] Register performers router in backend/src/main.py
- [x] T108a [P] [US8] Write API integration tests for Performers endpoints in backend/tests/integration/test_performers_api.py

### Frontend for User Story 8

- [x] T109 [P] [US8] Create performer TypeScript types in frontend/src/contracts/api/performer-api.ts
- [x] T110 [P] [US8] Create performers API service in frontend/src/services/performers.ts
- [x] T111 [US8] Create usePerformers hook in frontend/src/hooks/usePerformers.ts
- [x] T111a [P] [US8] Write hook tests for usePerformers in frontend/tests/hooks/usePerformers.test.ts (19 tests)
- [x] T112 [US8] Create PerformersTab component in frontend/src/components/directory/PerformersTab.tsx
- [x] T113 [US8] Create PerformerForm dialog component in frontend/src/components/directory/PerformerForm.tsx
- [x] T113a [P] [US8] Write component tests for PerformerForm in frontend/tests/components/PerformerForm.test.tsx (22 tests)
- [x] T114 [US8] Wire PerformersTab into DirectoryPage in frontend/src/pages/DirectoryPage.tsx
- [x] T115 [US8] Add performer management section to EventForm/EventDetails in frontend/src/components/events/EventForm.tsx (implemented in EventsPage.tsx EventDetails dialog with series sync)

### Implementation Notes for T115
- Performer add/remove operations sync across ALL events in a series (like Location and Organizer)
- Performer status is event-specific and does NOT sync across series
- Frontend shows sync notice for series events: "Adding or removing performers applies to all events in the series. Status can be set per event."
- **Performer Status Values:**
  - `announced` (default) - Performer announced but not yet confirmed (blue badge)
  - `confirmed` - Performer attendance confirmed (green badge)
  - `cancelled` - Performer cancelled (red badge)

**Checkpoint**: Performers can be created and associated with events

---

## Phase 12: User Story 10 - Configure Event Statuses (Priority: P3)

**Goal**: Allow configuration of event status options via the existing Config system

**Independent Test**: Add a custom status via Config API, verify it appears when editing events

**NOTE**: Uses existing Config table with new `event_statuses` category. Each status stored as key/value pair.

### Backend for User Story 10

- [x] T116 [US10] Add 'event_statuses' as valid config category in backend/src/services/config_service.py
- [x] T117 [US10] Seed default event statuses (future, confirmed, completed, cancelled) via migration 019_seed_default_event_statuses.py
- [x] T118 [US10] Add endpoint GET /api/config/event_statuses to return ordered status list in backend/src/api/config.py

### Frontend for User Story 10

- [x] T119 [US10] Create EventStatusesSection component for Config tab in frontend/src/components/settings/EventStatusesSection.tsx
- [x] T120 [US10] Integrate EventStatusesSection into ConfigTab in frontend/src/components/settings/ConfigTab.tsx
- [x] T121 [US10] Update EventForm to fetch statuses from /api/config/event_statuses (via useEventStatuses hook)

**Checkpoint**: Event statuses are configurable via Settings > Config

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Loading & Error States

- [x] T122a [P] Add loading states to EventsPage, DirectoryPage, SettingsPage
- [x] T122b [P] Add error boundaries and error toasts to new pages

### Dark Theme Compliance

- [x] T123a [P] Verify EventCalendar, EventCard, EventForm dark theme colors
- [x] T123b [P] Verify LocationForm, OrganizerForm, PerformerForm dark theme colors
- [x] T123c [P] Verify LogisticsSection status colors work in dark mode

### Accessibility

- [x] T124a [P] Add keyboard navigation to EventCalendar (arrow keys for date navigation)
- [x] T124b [P] Add ARIA labels to calendar events and status indicators
- [x] T124c [P] Test screen reader compatibility with EventDetails tooltip

### Validation

- [x] T125 Verify category matching is enforced across all entity associations
- [x] T126 Run database migrations and verify schema integrity
- [x] T127 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 9 (Phase 3)**: Categories - Must complete before other entity stories
- **User Stories 1-3 (Phases 4-6)**: Core calendar - P1 priority, can proceed after Categories
- **User Stories 4-7 (Phases 7-10)**: Extensions - P2 priority
- **User Stories 8, 10 (Phases 11-12)**: Nice-to-have - P3 priority
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 9 (Categories)**: Foundation for all - No dependencies on other stories
- **User Story 1 (Calendar View)**: Depends on Categories - Can start after Phase 3
- **User Story 2 (Create/Edit Events)**: Depends on US1 (needs calendar to display)
- **User Story 3 (Timezone Input)**: Depends on US2 (needs event form)
- **User Story 7 (KPIs)**: Depends on US1 (needs events service)
- **User Story 5 (Locations)**: Depends on Categories - Can run parallel to US1-3
- **User Story 6 (Organizers)**: Depends on Categories - Can run parallel to US1-3
- **User Story 4 (Logistics)**: Depends on US2, US5, US6 (needs event form and entity defaults)
- **User Story 8 (Performers)**: Depends on Categories - Can run parallel after US2
- **User Story 10 (Status Config)**: Stretch goal - After all core functionality

### Within Each User Story

- Models before services
- Services before API endpoints
- Backend before frontend (for types)
- API services before hooks
- Hooks before components
- Components before page integration

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All TypeScript types (T042, T076, T089, T102, T109) can be created in parallel
- All Pydantic schemas marked [P] can be created in parallel
- Once Foundational phase completes, US5 (Locations), US6 (Organizers), US8 (Performers) backend can run parallel to US1
- Frontend components within a story can often run in parallel
- SettingsPage (T022) and DirectoryPage (T025) can be created in parallel

---

## Parallel Example: User Story 1

```bash
# Launch backend schemas in parallel:
Task: "Create Pydantic schemas for Event in backend/src/schemas/event.py"
Task: "Create Pydantic schemas for EventSeries in backend/src/schemas/event_series.py"

# Launch frontend types/services in parallel:
Task: "Create event TypeScript types in frontend/src/contracts/api/event-api.ts"
Task: "Create events API service in frontend/src/services/events.ts"
```

---

## Implementation Strategy

### MVP First (User Stories 1-2 + Categories)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 9 (Categories - required foundation)
4. Complete Phase 4: User Story 1 (Calendar View)
5. Complete Phase 5: User Story 2 (Create/Edit Events)
6. **STOP and VALIDATE**: Test calendar display and event CRUD
7. Deploy/demo if ready - **MVP complete!**

### Incremental Delivery

1. Complete Setup + Foundational + Categories → Foundation ready
2. Add US1 (Calendar) + US2 (Events) → **MVP** - Can demonstrate calendar
3. Add US3 (Timezone) + US7 (KPIs) → Enhanced calendar experience
4. Add US5 (Locations) + US6 (Organizers) → Directory functionality
5. Add US4 (Logistics) → Preparation tracking
6. Add US8 (Performers) → Full feature set
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (Calendar View) → US2 (Events) → US3 (Timezone)
   - Developer B: US5 (Locations) → US6 (Organizers) → US4 (Logistics)
   - Developer C: US7 (KPIs) → US8 (Performers)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 163 |
| **Setup Tasks** | 2 |
| **Foundational Tasks** | 29 |
| **US9 (Categories)** | 8 |
| **US1 (Calendar View)** | 18 |
| **US2 (Create/Edit Events)** | 15 |
| **US3 (Timezone Input)** | 5 |
| **US7 (KPIs)** | 5 |
| **US5 (Locations)** | 19 |
| **US6 (Organizers)** | 19 |
| **US4 (Logistics)** | 7 |
| **US8 (Performers)** | 18 |
| **US10 (Status Config)** | 6 |
| **Polish Tasks** | 11 |

**Suggested MVP Scope**: Setup + Foundational + US9 (Categories) + US1 (Calendar View) + US2 (Create/Edit Events) = **72 tasks**

**Parallel Opportunities**: 55+ tasks marked with [P] can be executed in parallel with other tasks in their phase

**Test Coverage**: 30 test tasks included:
- Backend Unit (7): T019a, T020a, T038a, T053a, T071a, T085a, T103a
- Backend Integration (6): T030a, T041a, T056a, T075a, T088a, T108a
- Frontend (17): T028a, T044a, T045a, T057a, T065a, T068a, T078a, T080a, T081a, T091a, T093a, T093c, T098a, T111a, T113a, T124c (accessibility)
