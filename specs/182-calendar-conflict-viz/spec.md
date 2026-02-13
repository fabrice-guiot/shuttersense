# Feature Specification: Calendar Conflict Visualization & Event Picker

**Feature Branch**: `182-calendar-conflict-viz`
**Created**: 2026-02-13
**Status**: Draft
**Input**: GitHub Issue #182 — Calendar Conflict Visualization & Event Picker (PRD: `docs/prd/calendar-conflict-visualization.md`)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Detect Scheduling Conflicts on the Calendar (Priority: P1)

A team member browsing the event calendar sees visual warnings on days that contain conflicting events. Conflicts are detected automatically based on three rules: time overlaps (events that happen at the same time), distance conflicts (events on the same or consecutive days that are too far apart to attend both), and travel buffer violations (back-to-back travel events without enough rest days between them). The calendar cell shows an amber indicator with the number of conflict groups for that day. Individual event cards show a small conflict badge with a tooltip describing the conflict type and the other event involved.

**Why this priority**: Without conflict detection, the entire feature has no foundation. Visibility into scheduling collisions is the core value proposition that enables all downstream workflows (resolution, comparison, planning).

**Independent Test**: Can be fully tested by creating overlapping or geographically distant events and verifying that amber conflict indicators appear on the calendar grid and event cards. Delivers immediate awareness of scheduling problems.

**Acceptance Scenarios**:

1. **Given** two events on the same date with overlapping time ranges, **When** the user views the calendar, **Then** the calendar cell shows an amber warning indicator with the count "1" and both event cards display conflict badges.
2. **Given** two events on consecutive days at locations more than 50 miles apart (default threshold), **When** the user views the calendar, **Then** both days show amber warning indicators and each event card shows a distance conflict badge.
3. **Given** two travel-required events at non-co-located venues with only 1 day between them (below the default 3-day buffer), **When** the user views the calendar, **Then** both events show travel buffer violation badges.
4. **Given** an all-day event and a timed event on the same date, **When** the user views the calendar, **Then** a time overlap conflict is detected and displayed.
5. **Given** two events on the same date where neither has a location with coordinates, **When** the system checks for distance conflicts, **Then** no distance conflict is flagged (no false positives from missing data).
6. **Given** a conflict badge on an event card, **When** the user hovers over it, **Then** a tooltip shows the conflict type and the name of the conflicting event (e.g., "Time overlap with Festival Y").

---

### User Story 2 — Resolve Conflicts via Quick Actions (Priority: P2)

When a user clicks on a day with conflicts, the day detail dialog includes a "Conflicts" tab alongside the existing event list. This tab shows each conflict group as a card displaying the conflicting events side-by-side with their composite quality scores. The user can take quick-resolve actions: "Confirm" one event (marking it as planned and the others as skipped), or "Skip" to defer the decision. Resolved conflict groups change visual treatment (dimmed/dashed) to indicate they no longer need attention.

**Why this priority**: Detection alone creates awareness but not resolution. Quick-resolve actions turn awareness into decisions, which is the primary user goal — deciding which events to attend.

**Independent Test**: Can be tested by clicking a conflicted day, viewing the Conflicts tab, confirming one event, and verifying the attendance statuses update correctly and the conflict group status changes to "resolved."

**Acceptance Scenarios**:

1. **Given** a day with two conflicting events, **When** the user opens the day detail and selects the "Conflicts" tab, **Then** a conflict group card appears showing both events with their composite scores and conflict type label.
2. **Given** a conflict group with Event A (score 78) and Event B (score 62), **When** the user clicks "Confirm Event A," **Then** Event A's attendance is set to "planned," Event B's attendance is set to "skipped," and the conflict group status becomes "resolved."
3. **Given** a conflict group, **When** the user clicks "Skip," **Then** no attendance changes are made and the group remains "unresolved."
4. **Given** a resolved conflict group on the calendar, **When** the user views the calendar, **Then** the conflict indicator changes from solid amber to dashed gray to indicate resolution.
5. **Given** a conflict group with three events (A conflicts with B, B conflicts with C), **When** the user confirms Event B, **Then** both Event A and Event C are marked as "skipped" and the entire group is resolved.

---

### User Story 3 — Compare Events with Radar Charts (Priority: P3)

From the conflict resolution panel, the user clicks "Compare" to open a detailed comparison dialog. This dialog shows an overlaid radar chart (spider web) visualizing each event's quality scores across five dimensions: Venue Quality, Organizer Reputation, Performer Lineup, Logistics Ease, and Readiness. Below the chart, a dimension breakdown table shows exact numerical scores, and a side-by-side event detail summary displays key attributes (location, organizer, performer count, logistics status). The user can confirm an event directly from this dialog.

**Why this priority**: The radar chart transforms conflict resolution from a gut-feel decision into a data-driven comparison. It delivers the "event picker" value promised by the feature name.

**Independent Test**: Can be tested by opening the comparison dialog for two conflicting events and verifying the radar chart renders with correct dimension values, the breakdown table matches, and the confirm action works.

**Acceptance Scenarios**:

1. **Given** a conflict group with two events, **When** the user clicks "Compare," **Then** a dialog opens showing an overlaid radar chart with two distinct-colored polygons (one per event) on a 0–100 scale.
2. **Given** an event with location rating 4/5 and organizer rating 5/5, **When** the radar chart is displayed, **Then** the Venue Quality axis shows 80 and Organizer Reputation shows 100.
3. **Given** an event with 3 confirmed performers (default ceiling: 5), **When** the radar chart is displayed, **Then** the Performer Lineup axis shows 60.
4. **Given** an event with travel not required, time-off not required, and ticket not required, **When** the radar chart is displayed, **Then** the Logistics Ease axis shows 100.
5. **Given** the comparison dialog is open, **When** the user clicks "Confirm Event A," **Then** the same resolution logic as Story 2 executes and the dialog closes.
6. **Given** the comparison dialog on a mobile device, **When** the user views it, **Then** the radar chart stacks above the detail table in a responsive layout.

---

### User Story 4 — Configure Conflict Rules and Scoring Weights (Priority: P4)

A team administrator navigates to Settings > Configuration and sees two new sections: "Conflict Rules" and "Scoring Weights." In Conflict Rules, they can adjust: distance threshold (miles), consecutive window (days), travel buffer (days), co-location radius (miles), and performer ceiling (count). In Scoring Weights, they can adjust the relative weight of each scoring dimension (Venue Quality, Organizer Reputation, Performer Lineup, Logistics Ease, Readiness). Weights are relative — they do not need to sum to 100. A "Reset Defaults" button restores factory settings. Changes take effect immediately on the next conflict detection or scoring request.

**Why this priority**: Configurability lets teams tailor conflict sensitivity and scoring to their specific context (e.g., a team covering regional events needs a different distance threshold than one covering national tours). However, the system works well with defaults, so this is not blocking.

**Independent Test**: Can be tested by changing the distance threshold from 50 to 100 miles and verifying that two events 75 miles apart are no longer flagged as distance conflicts.

**Acceptance Scenarios**:

1. **Given** a newly created team, **When** an administrator opens Settings > Configuration, **Then** Conflict Rules shows default values: 50 miles distance threshold, 1 day consecutive window, 3 days travel buffer, 10 miles co-location radius, 5 performers ceiling.
2. **Given** a newly created team, **When** an administrator opens Settings > Configuration, **Then** Scoring Weights shows default values of 20 for each of the five dimensions.
3. **Given** the administrator changes the distance threshold to 100 miles, **When** they save and view the calendar, **Then** events 75 miles apart are no longer flagged as distance conflicts.
4. **Given** a scoring weight for Venue Quality set to 40 and all others at 10, **When** an event is scored, **Then** the composite score reflects Venue Quality being 4x more influential.
5. **Given** a scoring weight set to 0, **When** the radar chart is displayed, **Then** that dimension's axis is visually dimmed but still visible for reference, and it contributes nothing to the composite score.
6. **Given** modified settings, **When** the administrator clicks "Reset Defaults," **Then** all values revert to the system defaults.

---

### User Story 5 — Unified Date Range Picker for All List Views (Priority: P5)

All non-calendar views on the Events page (preset filters and Timeline Planner) gain a shared date range picker that controls which events are loaded. The calendar view remains unchanged (forced 1-month window with month scroll). The date range picker offers predefined rolling windows (Next 30 / 60 / 90 days), predefined calendar-month windows (Next 1 / 2 / 3 / 6 months, aligned to 1st-through-end-of-month), and a custom range where the user picks explicit start and end dates. There is no "All" option — every list view is bounded by a date range. The existing "Upcoming 30d" preset becomes the default range (Next 30 days). Event lists render with infinite scroll within the bounded result set rather than classic pagination.

**Why this priority**: The existing preset list views (Needs Tickets, Needs PTO, Needs Travel) have no user-controllable time window, and the new Planner view needs its own range. Introducing the date range picker as a shared component ensures consistency across all list-based views and avoids asymmetric UX patterns. This is a prerequisite for the Planner view.

**Independent Test**: Can be tested by selecting a preset filter (e.g., Needs Tickets), changing the date range to "Next 60 days," and verifying that only events within that window appear. Then switching to "Next 1 month" and verifying the results are bounded to calendar month boundaries.

**Acceptance Scenarios**:

1. **Given** the user clicks a preset filter button (e.g., Needs Tickets), **When** the list view loads, **Then** a date range picker appears above the list defaulting to "Next 30 days."
2. **Given** the date range picker is set to "Next 60 days," **When** the user selects "Next 3 months" instead, **Then** the list reloads showing events from today through the end of the 3rd calendar month.
3. **Given** the user selects "Custom" in the date range picker, **When** they enter a start date of March 1 and end date of May 15, **Then** the list shows only events within that custom range.
4. **Given** a date range that returns many events, **When** the user scrolls to the bottom of the list, **Then** additional events load automatically (infinite scroll) until all events in the range are displayed.
5. **Given** the user is in calendar view, **When** they look at the controls, **Then** no date range picker is shown — the calendar keeps its existing month navigation (prev/next/today).
6. **Given** the user switches from a preset view back to the calendar, **When** the calendar loads, **Then** the date range picker disappears and the calendar month navigation is restored.
7. **Given** the date range picker, **When** the user reviews the options, **Then** there is no "All" or unbounded option available.

---

### User Story 6 — Plan Ahead with the Timeline Planner (Priority: P6)

The Events page gains a new "Planner" view mode. The Planner shows a scrollable chronological timeline of upcoming events. Each event is displayed as a marker with: a composite score bar (filled proportionally to the 0–100 score), mini dimension segments below the bar showing individual dimension contributions as colored segments (a linearized version of the radar chart), and the event name and date. Events in the same conflict group are connected by vertical amber lines on the left margin with the conflict type labeled. The Planner uses the unified date range picker (from Story 5) to control its time window and additionally offers filters for category, conflicts-only, and unresolved-only. Clicking an event marker expands it inline to show its full radar chart; clicking a conflict connector shows the overlaid comparison.

**Why this priority**: The timeline planner is the most ambitious UX component. It transforms the calendar from showing event presence/absence into showing event quality over time. It depends on Stories 1–4 being functional and the unified date range picker (Story 5) being available.

**Independent Test**: Can be tested by switching to the Planner view and verifying that upcoming events appear in chronological order with score bars, conflict connectors link related events, and filters narrow the displayed set.

**Acceptance Scenarios**:

1. **Given** the user has several upcoming events, **When** they activate the Planner view on the Events page, **Then** a scrollable timeline appears showing events in chronological order grouped by month, with the date range picker defaulting to "Next 30 days."
2. **Given** an event with a composite score of 78, **When** it appears in the timeline, **Then** the score bar fills to approximately 78% of its maximum width with the score labeled "Score: 78."
3. **Given** two events in the same conflict group, **When** they appear in the timeline, **Then** a vertical amber line connects them on the left margin with a label showing the conflict type.
4. **Given** the user selects "Conflicts only" filter, **When** the timeline refreshes, **Then** only events involved in at least one conflict group are shown.
5. **Given** the user clicks an event marker, **When** the marker expands, **Then** the full radar chart for that event is displayed inline.
6. **Given** a resolved conflict group, **When** it appears in the timeline, **Then** the connector line is dashed gray instead of solid amber.
7. **Given** the Planner is viewed on a mobile device, **When** events are displayed, **Then** dimension micro-segments are hidden and only the composite score bar is shown; tapping an event opens a bottom sheet with the radar chart.

---

### User Story 7 — View Planner KPIs and Receive Conflict Notifications (Priority: P7)

When the user is on the Planner view, the page header displays relevant KPIs: total conflict groups, unresolved conflicts, events scored, and average quality score. When a new event is created or updated in a way that introduces a new conflict, the user receives a notification alerting them to the new scheduling conflict.

**Why this priority**: KPIs and notifications are polish items that improve the experience but do not introduce new core functionality. The system is fully usable without them.

**Independent Test**: Can be tested by navigating to the Planner view and verifying KPI badges appear with correct counts, and by creating a conflicting event and verifying a notification is generated.

**Acceptance Scenarios**:

1. **Given** the user is on the Planner view with 3 conflict groups (2 unresolved, 1 resolved), **When** the page loads, **Then** the header shows "Conflicts: 3," "Unresolved: 2," and related KPIs.
2. **Given** the user creates a new event that overlaps with an existing event, **When** the event is saved, **Then** a notification is generated informing the user of the new conflict.
3. **Given** the user resolves all conflicts, **When** the header KPIs refresh, **Then** "Unresolved" shows 0.

---

### Edge Cases

- What happens when an event has no location (null coordinates)? Distance conflict detection skips this event entirely — no false positives are generated.
- What happens when an event has no organizer or no performers? The corresponding scoring dimension uses a neutral default (50 for ratings, 0 for performer count), ensuring a score is always computable.
- What happens when all events on a day are in a single transitive conflict group (e.g., A conflicts with B, B conflicts with C)? They form one conflict group. The user resolves the entire group by confirming one event.
- What happens when an event's date or location changes after a conflict was resolved? The conflict detection recomputes on the next request — a previously resolved group may become unresolved again if the change introduces new conflicts.
- What happens with very large numbers of events (hundreds per quarter)? The system handles up to several hundred events per team per date range query without noticeable delay.
- What happens when a team has never configured scoring weights? Default equal weights (20 each) are automatically provisioned when the team is created.
- What happens if a scoring weight is set to 0? That dimension is excluded from the composite score calculation and its radar chart axis is dimmed but still visible.
- What happens with a single event on a day (no conflicts)? No conflict indicators appear. The event can still be scored and viewed in the timeline planner with its quality visualization.
- What happens when the user selects "Next 1 month" vs "Next 30 days"? "Next 30 days" is a rolling window from today; "Next 1 month" covers from the 1st of the current month through the end of the month. Both are valid and produce different result sets.
- What happens when the user's custom date range returns zero events? The list view shows an empty state message appropriate to the active preset or planner view.
- What happens when the user switches from a preset list view to the calendar? The date range picker disappears and the calendar's own month navigation takes over. Switching back to a preset restores the last-selected date range.

## Requirements *(mandatory)*

### Functional Requirements

#### Conflict Detection

- **FR-001**: System MUST detect time overlap conflicts when two events on the same date have intersecting time ranges.
- **FR-002**: System MUST detect time overlap conflicts between an all-day event and any other event (timed or all-day) on the same date.
- **FR-003**: System MUST treat two timed events on the same date that lack start/end times as conflicting (conservative default).
- **FR-004**: System MUST detect distance conflicts when two events on the same date or within a configurable consecutive window are farther apart than the configured distance threshold.
- **FR-005**: System MUST use great-circle (haversine) distance when computing geographic distance between event locations.
- **FR-006**: System MUST exclude events without geocoded location coordinates from distance conflict detection.
- **FR-007**: System MUST detect travel buffer violations when two travel-required, non-co-located events have fewer than the configured buffer days between them.
- **FR-008**: System MUST group transitively connected conflicting events into conflict groups (connected components in the conflict graph).
- **FR-009**: System MUST track conflict group resolution status: unresolved, partially resolved, or resolved (resolved = at most one event in the group has attendance "planned" or "attended").

#### Event Quality Scoring

- **FR-010**: System MUST score each event across five dimensions: Venue Quality (from location rating), Organizer Reputation (from organizer rating), Performer Lineup (from confirmed performer count), Logistics Ease (from travel/time-off/ticket requirements), and Readiness (from booking statuses).
- **FR-011**: System MUST normalize all dimension scores to a 0–100 scale.
- **FR-012**: System MUST compute a composite score as the weighted average of dimension scores using team-configured weights.
- **FR-013**: System MUST use neutral defaults for missing data: 50 for null ratings, 0 for zero performers.
- **FR-014**: System MUST support an extensible scoring model so new dimensions can be added in the future without restructuring the user interface.

#### Calendar Conflict Indicators

- **FR-015**: Calendar cells MUST show an amber warning indicator with the count of conflict groups when the day contains conflicting events.
- **FR-016**: Event cards MUST display a conflict badge for events involved in at least one conflict.
- **FR-017**: Conflict badges MUST show a tooltip describing the conflict type and the other event(s) involved.

#### Conflict Resolution

- **FR-018**: The day detail dialog MUST include a "Conflicts" tab when the selected day has conflicts.
- **FR-019**: Each conflict group card MUST show the conflicting events with their composite scores and the conflict type.
- **FR-020**: Users MUST be able to confirm one event in a conflict group, which sets its attendance to "planned" and the others to "skipped."
- **FR-021**: Users MUST be able to skip (defer) a conflict resolution decision without changing any attendance values.
- **FR-022**: Resolved conflict groups MUST visually transition from solid amber to dashed gray indicators.

#### Radar Chart Comparison

- **FR-023**: The comparison dialog MUST display an overlaid radar chart with distinct-colored polygons for each event in a conflict group.
- **FR-024**: Radar chart axes MUST be labeled with dimension names and scale from 0 to 100.
- **FR-025**: The comparison dialog MUST include a dimension breakdown table showing exact numerical scores per event.
- **FR-026**: The comparison dialog MUST include a side-by-side event detail summary (location, organizer, performer count, logistics statuses).
- **FR-027**: Users MUST be able to confirm an event directly from the comparison dialog.

#### Unified Date Range Picker

- **FR-028**: All non-calendar list views (preset filters and Planner) MUST display a shared date range picker that controls which events are loaded.
- **FR-029**: The calendar view MUST NOT show the date range picker — it retains its existing month navigation (prev/next/today).
- **FR-030**: The date range picker MUST offer rolling window presets: Next 30 days, Next 60 days, Next 90 days.
- **FR-031**: The date range picker MUST offer calendar-month window presets: Next 1 month, Next 2 months, Next 3 months, Next 6 months (aligned to 1st-through-end-of-month boundaries).
- **FR-032**: The date range picker MUST offer a custom range option where the user selects explicit start and end dates.
- **FR-033**: The date range picker MUST NOT offer an "All" or unbounded option — every list view MUST be bounded by a date range.
- **FR-034**: The default date range MUST be "Next 30 days" (matching the behavior of the existing "Upcoming" preset).
- **FR-035**: Event lists within all non-calendar views MUST use infinite scroll within the bounded result set rather than classic pagination.

#### Timeline Planner

- **FR-036**: The Events page MUST include a "Planner" view mode alongside the existing Calendar view and preset filters.
- **FR-037**: The Planner MUST use the unified date range picker (FR-028) to control its time window.
- **FR-038**: The Planner MUST display events in a scrollable chronological timeline grouped by month.
- **FR-039**: Each timeline marker MUST show a composite score bar (filled proportional to the 0–100 score) and the event name/date.
- **FR-040**: Each timeline marker MUST show dimension micro-segments (linearized radar) below the score bar on non-mobile viewports.
- **FR-041**: Events in the same conflict group MUST be connected by a vertical amber line on the left margin with a conflict type label.
- **FR-042**: Users MUST be able to filter the timeline by category, conflicts-only, and unresolved-only (in addition to the date range picker).
- **FR-043**: Clicking an event marker MUST expand it inline to show the full radar chart.
- **FR-044**: Clicking a conflict connector MUST expand to show the overlaid radar comparison.
- **FR-045**: On mobile, dimension micro-segments MUST be hidden, and event expansion MUST use a bottom sheet dialog.

#### Settings

- **FR-046**: System MUST provide a "Conflict Rules" configuration section with five settings: distance threshold (miles), consecutive window (days), travel buffer (days), co-location radius (miles), and performer ceiling (count).
- **FR-047**: System MUST provide a "Scoring Weights" configuration section with one weight per scoring dimension (0–100 range each).
- **FR-048**: Setting a scoring weight to 0 MUST exclude that dimension from the composite score and dim its radar chart axis.
- **FR-049**: Both configuration sections MUST include a "Reset Defaults" action that restores factory values.
- **FR-050**: Configuration changes MUST take effect on the next conflict detection or scoring request without requiring a page refresh.

#### Team Provisioning

- **FR-051**: System MUST automatically provision default conflict rules and scoring weights when a new team is created.
- **FR-052**: System MUST backfill default conflict rules and scoring weights for all existing teams that do not yet have them.

#### KPI & Notifications

- **FR-053**: When the Planner view is active, the page header MUST display KPIs: total conflict groups, unresolved count, events scored, and average quality score.
- **FR-054**: System MUST generate a notification when a new or updated event introduces a scheduling conflict.

### Key Entities

- **Conflict Group**: A set of events connected by one or more conflict edges. Has an identifier, a list of member events, a list of conflict edges (pairs with conflict type and detail), and a resolution status (unresolved / partially resolved / resolved). Computed at query time, not persisted.
- **Conflict Edge**: A relationship between two events indicating a specific conflict. Has a conflict type (time overlap, distance, travel buffer), the two involved events, and a human-readable description of the conflict.
- **Event Scores**: A set of five dimension scores (0–100 each) and a weighted composite score for a single event. Computed at query time from event, location, organizer, and performer data.
- **Conflict Rules Configuration**: Five team-scoped settings controlling how conflicts are detected: distance threshold, consecutive window, travel buffer, co-location radius, and performer ceiling.
- **Scoring Weights Configuration**: Five team-scoped settings controlling how dimension scores contribute to the composite: one relative weight per dimension.

## Assumptions

- The existing event model already contains all fields needed for conflict detection (`event_date`, `start_time`, `end_time`, `is_all_day`, `travel_required`, `attendance`) and scoring (`ticket_required`, `timeoff_required`, `ticket_status`, `timeoff_status`, `travel_status`).
- Location coordinates (`latitude`, `longitude`) and ratings are already populated for locations that have been geocoded. Events at locations without coordinates are silently excluded from distance-based checks.
- Organizer and performer data (ratings, confirmed status) are already tracked in the existing data model.
- The existing team configuration storage mechanism can accommodate new configuration categories without schema changes.
- The existing charting library already in the project dependencies supports radar chart visualization — no new library is needed.
- Conflict groups are computed at query time (not persisted), keeping the data model simple and avoiding stale conflict data when events change.
- Distance is computed as great-circle (haversine) distance; actual driving/transit time is out of scope.
- Conflict detection performance is acceptable for the expected event volumes (hundreds of events per team per quarter).

## Scope Boundaries

**In scope:**
- Automated detection of three conflict types (time overlap, distance, travel buffer)
- Five-dimension event quality scoring with configurable weights
- Conflict indicators on the calendar grid and event cards
- Conflict resolution panel in day detail dialog
- Radar chart comparison dialog for side-by-side event evaluation
- Unified date range picker for all non-calendar list views (presets + planner) with rolling, calendar-month, and custom range options
- Infinite scroll for date-range-bounded list views (replaces unbounded lists)
- Timeline planner view with score bars, dimension micro-segments, and conflict connectors
- Conflict rules and scoring weights settings
- Default provisioning for new and existing teams
- KPI display and conflict notifications

**Out of scope:**
- Automatic conflict resolution (system recommends, user decides)
- External calendar sync (Google Calendar, Outlook, etc.)
- Actual route/transit time calculation (only great-circle distance)
- Budget/expense tracking
- Historical scoring dimensions from past analysis results (deferred to a follow-up)
- Unit preference toggle (miles vs. kilometers) for distance settings

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of time overlap conflicts among events with defined time ranges are correctly detected and displayed.
- **SC-002**: Greater than 95% of distance conflicts are correctly detected for events with geocoded locations (excludes events without coordinates).
- **SC-003**: Users can identify a scheduling conflict from the calendar in under 5 seconds (visible badge + tooltip on hover).
- **SC-004**: Users can resolve a conflict (confirm one event, skip others) in under 3 clicks from the calendar view.
- **SC-005**: Users can compare two conflicting events across all five quality dimensions in a single view (radar chart + breakdown table) without navigating away.
- **SC-006**: Greater than 70% of detected conflict groups are resolved by users within 7 days of detection.
- **SC-007**: Greater than 40% of active users visit the Timeline Planner view within the first month after launch.
- **SC-008**: Greater than 80% of upcoming events display a composite quality score (requires location and/or organizer data).
- **SC-009**: Configuration changes to conflict rules or scoring weights are reflected in conflict detection and scoring results immediately on the next request.
- **SC-010**: All conflict detection, scoring, and visualization features work correctly on both desktop and mobile viewports with appropriate responsive adaptations.
