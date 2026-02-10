# PRD: Calendar Conflict Visualization & Event Picker

**Status**: Draft
**Created**: 2026-02-10
**Last Updated**: 2026-02-10
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Design System](../../frontend/docs/design-system.md)
- [Events Feature (Issue #39)](../../specs/011-calendar-events/)

---

## Executive Summary

This PRD defines a **Calendar Conflict Visualization & Event Picker** feature for ShutterSense. The feature helps users visualize scheduling conflicts among upcoming events, compare conflicting events side-by-side using multi-dimensional scoring, and make informed attendance decisions from a unified planning view.

Events conflict when they overlap in time, when they are geographically too far apart to attend consecutively (distance threshold), or when back-to-back travel events lack a sufficient rest buffer between them (travel buffer). Conflict rules are configured via new settings on the Settings page.

Each event is scored across multiple quality dimensions (location rating, organizer rating, performer count, travel cost, etc.) displayed as a **radar chart** (spider web). Conflicting events are compared side-by-side with overlaid or juxtaposed radar charts. A new **Timeline Planner** view projects these quality scores onto a chronological timeline, giving users a forward-looking view of their calendar quality alongside conflict indicators.

---

## Background

### Current State

The Events page (`/events`) provides a **month-grid calendar** for browsing and managing events. Users can create, edit, and delete events, track logistics (tickets, time-off, travel), and view event details in modals. Events have associated locations (with geocoded coordinates), organizers (with ratings), and performers.

However, the current calendar offers **no conflict detection or decision-support tooling**:

1. **No overlap detection** — Two events on the same date/time show as separate entries with no visual warning.
2. **No geographic proximity awareness** — Events at distant locations on consecutive days are not flagged as logistically impractical.
3. **No travel buffer enforcement** — Back-to-back travel events with insufficient rest days are invisible.
4. **No multi-dimensional comparison** — Users have no way to compare competing events across quality dimensions (location quality, organizer reputation, performer lineup, cost).
5. **No forward-planning view** — The month grid shows presence/absence of events but not their relative quality or the overall shape of the upcoming calendar.

### Affected Files (Existing)

- `frontend/src/pages/EventsPage.tsx` — Current calendar page (will gain a new "Planner" tab or sub-view)
- `frontend/src/components/events/EventCalendar.tsx` — Month grid (will gain conflict indicators)
- `frontend/src/components/events/EventCard.tsx` — Event cards (will gain conflict badge)
- `frontend/src/contracts/api/event-api.ts` — Event types (will be extended with conflict/score data)
- `frontend/src/contracts/api/config-api.ts` — Config types (new conflict settings)
- `frontend/src/pages/SettingsPage.tsx` — Settings page (new "Conflict Rules" section)
- `backend/src/api/events.py` — Event API routes (new conflict detection endpoint)
- `backend/src/api/config.py` — Config API (new conflict config category)
- `backend/src/schemas/event.py` — Event schemas (conflict/score response types)
- `backend/src/services/event_service.py` — Event service (conflict detection logic)
- `backend/src/models/location.py` — Location model (has `latitude`/`longitude` already)

### Problem Statement

- **Missed conflicts**: Users discover scheduling collisions only by manually scanning the calendar, often too late to change plans.
- **No decision framework**: When two events compete for the same slot, users lack a structured way to weigh tradeoffs (venue quality vs. travel cost vs. performer lineup).
- **No forward visibility**: Users cannot see the "shape" of their upcoming calendar — whether the next 3 months are dense or sparse, high-quality or routine.
- **Geographic blindness**: The calendar treats all events as interchangeable regardless of physical distance, leading to impractical itineraries.

### Strategic Context

ShutterSense manages event-driven photo workflows where attending the right events directly impacts content quality. Choosing between overlapping events (or between an event that requires expensive travel and a local one) is a recurring, high-stakes decision. Providing data-driven decision support transforms the calendar from a passive display into an active planning tool.

---

## Goals

### Primary Goals

1. **Detect and visualize conflicts** — Automatically identify time overlaps, distance-based conflicts, and travel buffer violations; display them as clear visual indicators in the calendar.
2. **Enable structured comparison** — Provide side-by-side radar chart (spider web) comparison of conflicting events across configurable quality dimensions.
3. **Support attendance decisions** — Allow users to resolve conflicts by confirming attendance on one event, with the system tracking the decision and dimming/skipping the alternative.
4. **Project calendar quality over time** — Introduce a timeline planner view that shows upcoming events as scored markers on a chronological axis, making calendar density and quality visible at a glance.

### Secondary Goals

5. **Configurable conflict rules** — Allow teams to tune distance thresholds and travel buffer days via Settings, since acceptable travel varies by context.
6. **Extensible scoring model** — Design the scoring framework so new dimensions (e.g., historical event score from past results) can be added without restructuring the UI.
7. **Mobile-friendly** — Ensure the conflict visualization and planner view work on mobile with progressive disclosure (summary first, detail on tap).

### Non-Goals

- **Automatic conflict resolution** — The system recommends but does not auto-decide. The user always makes the final attendance choice.
- **External calendar sync** — Integration with Google Calendar, Outlook, etc. is out of scope for this feature.
- **Route/transit time calculation** — Distance is computed as great-circle (haversine); actual driving/transit time is not calculated.
- **Budget tracking** — While travel cost is a scoring dimension, the system does not track actual expenses.

---

## Conflict Detection Model

### Conflict Types

Three types of conflicts are detected, each configurable independently:

#### Type 1: Time Overlap

Two events conflict when their time ranges intersect on the same date.

**Rules:**
- **Timed events**: `event_A.start_time < event_B.end_time AND event_B.start_time < event_A.end_time` on the same `event_date`.
- **All-day events**: Any two all-day events on the same date conflict. An all-day event conflicts with any timed event on the same date.
- **Same-day heuristic**: Two timed events on the same date that have no `start_time`/`end_time` set are treated as conflicting (conservative default).

#### Type 2: Distance Conflict

Two events on the same date or consecutive dates conflict if they are farther apart than a configurable distance threshold, making it impractical to attend both.

**Rules:**
- Both events must have locations with geocoded coordinates (`latitude`, `longitude`).
- Distance computed using the **Haversine formula** (great-circle distance).
- If `haversine(event_A.location, event_B.location) > distance_threshold_miles`, the events are in distance conflict.
- Events without geocoded locations are excluded from distance conflict detection (no false positives).
- Applies to events on the same date or on dates within a configurable "consecutive window" (default: 1 day, meaning same-day and next-day events are checked).

**Settings:**
- `conflict_distance_threshold_miles` (default: 50) — Maximum distance in miles between two events before they are considered in conflict.
- `conflict_consecutive_window_days` (default: 1) — Number of days forward to check for distance conflicts (0 = same-day only, 1 = same-day + next-day).

#### Type 3: Travel Buffer Violation

Two events that both require travel and are not co-located conflict if they lack sufficient buffer days between them.

**Rules:**
- Both events must have `travel_required = true`.
- Events must NOT be co-located (distance > `conflict_colocation_radius_miles`).
- If `abs(event_A.event_date - event_B.event_date) < travel_buffer_days`, they are in travel buffer conflict.

**Settings:**
- `conflict_travel_buffer_days` (default: 3) — Minimum days required between two non-co-located travel events.
- `conflict_colocation_radius_miles` (default: 10) — Two locations within this radius are considered "co-located" and exempt from the travel buffer rule.

### Conflict Group

When multiple events conflict with each other (directly or transitively), they form a **conflict group**. A conflict group is the connected component in the event-conflict graph. For example, if A conflicts with B and B conflicts with C, then {A, B, C} form one conflict group even if A does not directly conflict with C.

Each conflict group has:
- A unique identifier (for frontend tracking)
- A list of member events
- A list of edges (pairs of conflicting events with conflict type)
- A resolution status: `unresolved` | `partially_resolved` | `resolved`

A group is `resolved` when at most one event in the group has `attendance = planned` or `attendance = attended` — i.e., the user has decided which event(s) to skip.

---

## Event Quality Scoring Model

### Dimensions

Each event is scored across multiple dimensions, normalized to a 0–100 scale for radar chart display. The initial dimensions are:

| Dimension | Source Field(s) | Scoring Logic |
|-----------|----------------|---------------|
| **Venue Quality** | `location.rating` (1–5) | `rating * 20` → 0–100. Null = 50 (neutral). |
| **Organizer Reputation** | `organizer.rating` (1–5) | `rating * 20` → 0–100. Null = 50 (neutral). |
| **Performer Lineup** | `performers.length`, performer `status` | Confirmed count mapped to 0–100 via configurable ceiling (default: 5 performers = 100). |
| **Logistics Ease** | `travel_required`, `timeoff_required`, `ticket_required` | Each `false` = +33. All false = 100 (easy). All true = 0 (hard). |
| **Readiness** | `ticket_status`, `timeoff_status`, `travel_status` | Each resolved status (ready/approved/booked) = +33 of its share. Fully ready = 100. |

**Extensibility**: The scoring engine accepts a list of `ScoringDimension` definitions. New dimensions (e.g., "historical event quality" derived from past analysis results) can be added by registering a new dimension with a name, data accessor, and normalization function. The radar chart and timeline marker automatically adapt to any number of dimensions (tested up to 8; beyond that, the chart becomes less readable).

### Composite Score

A single composite score (0–100) is computed as the **weighted average** of all dimension scores. Default weights are equal, but users can adjust weights in Settings (future enhancement — not in initial release). The composite score is used for:

- Timeline marker color intensity (higher = more saturated)
- Sorting within conflict groups (recommended event = highest composite)
- Quick comparison when radar chart detail is not needed

---

## User Experience Design

### 1. Conflict Indicators on the Calendar Grid

The existing month-grid calendar gains conflict awareness:

**Visual Treatment:**
- Days with conflicting events show a **warning indicator** (orange/amber triangle icon) in the top-right corner of the calendar cell.
- The indicator shows the count of conflict groups for that day (e.g., "2" means two separate conflict groups involve events on that day).
- Clicking a day with conflicts opens the day detail dialog, which now includes a **"Conflicts"** tab alongside the existing event list.

**Event Card Enhancement:**
- Events involved in conflicts gain a small **conflict badge** (amber dot or `AlertTriangle` icon) next to their category badge.
- The badge tooltip shows the conflict type(s): "Time overlap with Event X", "Too far from Event Y (120 mi)", "Travel buffer: only 1 day between Event X".

### 2. Conflict Resolution Panel (Day Detail Enhancement)

When a day has conflicts, the day detail dialog adds a **Conflict Resolution** section:

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  January 15, 2026                          [Close]  │
├─────────────────────────────────────────────────────┤
│  [Events]  [Conflicts (2)]                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─ Conflict Group 1 ────────────────────────────┐  │
│  │  ⚠ Time Overlap                               │  │
│  │                                                │  │
│  │  ┌──────────┐     ┌──────────┐                │  │
│  │  │  Event A  │ vs  │  Event B  │               │  │
│  │  │  ★★★★☆   │     │  ★★★☆☆   │               │  │
│  │  │  Score 78 │     │  Score 62 │               │  │
│  │  └──────────┘     └──────────┘                │  │
│  │                                                │  │
│  │  [Compare ↗]  [Confirm A] [Confirm B] [Skip]  │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
│  ┌─ Conflict Group 2 ────────────────────────────┐  │
│  │  ⚠ Distance: 85 miles apart                   │  │
│  │  ...                                           │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Actions:**
- **Compare** — Opens the side-by-side radar chart comparison dialog.
- **Confirm [Event]** — Sets `attendance = planned` on the chosen event and `attendance = skipped` on the other(s) in the group.
- **Skip** — Defers the decision (no attendance change).

### 3. Radar Chart Comparison Dialog

The comparison dialog provides a detailed multi-dimensional view of two or more events from a conflict group:

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│  Compare Events                                     [Close]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────── Radar Chart ───────────┐                       │
│  │                                   │    Event A (blue)     │
│  │         Venue Quality             │    ● Concert X        │
│  │            ╱    ╲                 │      Score: 78        │
│  │     Ready/     \  Organizer       │                       │
│  │     ness  ╲     ╱  Reputation     │    Event B (orange)   │
│  │            ╲   ╱                  │    ● Festival Y       │
│  │      Logistics  Performers        │      Score: 62        │
│  │          Ease                     │                       │
│  │                                   │    ─── = Event A      │
│  │    [Overlaid radar polygons]      │    --- = Event B      │
│  └───────────────────────────────────┘                       │
│                                                              │
│  ┌─────────── Dimension Breakdown ───────────┐               │
│  │ Dimension           │  Event A │  Event B  │              │
│  │─────────────────────┼──────────┼───────────│              │
│  │ Venue Quality       │   80     │   60      │              │
│  │ Organizer Rep.      │   90     │   80      │              │
│  │ Performer Lineup    │   60     │   40      │              │
│  │ Logistics Ease      │   67     │   33      │              │
│  │ Readiness           │   100    │   67      │              │
│  └────────────────────────────────────────────┘              │
│                                                              │
│  ┌─── Event Details Side-by-Side ───┐                        │
│  │  📍 Venue Arena, NYC    │  📍 Open Field, Austin         │
│  │  🏢 LiveNation ★★★★☆   │  🏢 SXSW Org ★★★☆☆           │
│  │  👥 3 performers        │  👥 2 performers               │
│  │  ✈️  No travel           │  ✈️  Travel required           │
│  │  🎫 Ticket ready        │  🎫 Not purchased              │
│  └──────────────────────────────────┘                        │
│                                                              │
│        [Confirm Event A]    [Confirm Event B]    [Cancel]    │
└──────────────────────────────────────────────────────────────┘
```

**Radar Chart Specifics:**
- Uses **Recharts RadarChart** component (already in the dependency tree).
- Two (or more) event polygons overlaid on the same chart with distinct colors from `CHART_COLORS`.
- Axes labeled with dimension names. Axis scale 0–100.
- Interactive tooltips on hover showing exact values.
- Responsive: on mobile, chart stacks above the detail table.

**Design System Compliance:**
- Colors from design tokens (`--chart-1` through `--chart-5`).
- Uses Card, Dialog, Button, Badge components from shadcn/ui.
- Status colors follow existing semantic mappings.
- Follows Single Title Pattern — dialog title is the only heading.

### 4. Timeline Planner View

A new view accessible from the Events page that provides a forward-looking, scrollable timeline of upcoming events with quality visualization.

**Access:** New tab on the Events page: `[Calendar] [Planner]`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  Events                                      [KPI Stats]    │
├─────────────────────────────────────────────────────────────┤
│  [Calendar]  [Planner]                     [+ New Event]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── Filters ──────────────────────────────────────────┐   │
│  │ Range: [Next 3 months ▾]  Category: [All ▾]          │   │
│  │ Show: [☑ Conflicts only] [☑ Unresolved only]         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ── February 2026 ──────────────────────────────────────    │
│                                                             │
│  Feb 8   ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  Concert X     │
│          █████████░░░  Score: 78                            │
│          [Venue ████ | Org ████ | Perf ███ | Ease ██]       │
│                                                             │
│  Feb 8   ●━━━━━━━━━━━━━━━━━━━━━━  ⚠ Festival Y            │
│          ██████░░░░░░  Score: 62                            │
│          [Venue ███ | Org ███ | Perf ██ | Ease █]           │
│          ├── ⚠ Time overlap with Concert X                  │
│                                                             │
│  Feb 15  ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  Gallery Opening  │
│          ████████████  Score: 85                            │
│          [Venue █████ | Org ████ | Perf ████ | Ease ████]   │
│                                                             │
│  ── March 2026 ─────────────────────────────────────────    │
│                                                             │
│  Mar 1   ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ⚠ Workshop A      │
│          ███████░░░░░  Score: 68                            │
│          ├── ⚠ Travel buffer: 2d to Workshop B (need 3d)    │
│                                                             │
│  Mar 3   ●━━━━━━━━━━━━━━━━━━━━━━━━━  ⚠ Workshop B          │
│          ██████░░░░░░  Score: 55                            │
│                                                             │
│  ...                                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Timeline Marker Design — Projecting the Radar Chart:**

The key UX challenge is representing multi-dimensional quality in a compact, linear format. The approach:

1. **Composite Score Bar**: Each event shows a horizontal bar whose filled length represents the composite score (0–100). The bar color is the event's category color. Bar intensity (opacity) increases with score.

2. **Mini Dimension Segments**: Below the main bar, a segmented micro-bar shows the individual dimension contributions. Each segment is a distinct color (matching the radar chart axes) and its width is proportional to that dimension's score. This is a **linearized radar chart** — the same data as the spider web, but projected into a 1D bar. Hovering a segment shows the dimension name and value.

3. **Conflict Connectors**: Events in the same conflict group are connected by a vertical amber line on the left margin. The conflict type is shown as a label on the connector. Unresolved conflicts use a solid line; resolved conflicts use a dashed gray line.

4. **Score Color Mapping**: The composite score maps to a background tint:
   - 80–100: green tint (strong event)
   - 60–79: blue tint (good event)
   - 40–59: yellow tint (average event)
   - 0–39: gray tint (weak event)

5. **Expand to Radar**: Clicking a timeline marker expands it inline to show the full radar chart for that event. Clicking a conflict connector expands to show the overlaid radar comparison.

**Mobile Adaptation:**
- Mini dimension segments hidden on mobile; only composite score bar shown.
- Conflict connectors simplified to amber badges on event cards.
- Tap to expand shows radar chart in a bottom sheet dialog.

### 5. Settings: Conflict Rules Configuration

A new section in the Settings page under the Configuration tab.

**Location:** Settings > Configuration > Conflict Rules (new section)

**Settings UI:**
```
┌─── Conflict Rules ──────────────────────────────────────┐
│                                                         │
│  Distance Threshold                                     │
│  Maximum miles between events before flagging a         │
│  distance conflict.                                     │
│  [  50  ] miles                                         │
│                                                         │
│  Consecutive Window                                     │
│  Number of days forward to check for distance           │
│  conflicts (0 = same-day only).                         │
│  [  1  ] days                                           │
│                                                         │
│  Travel Buffer                                          │
│  Minimum days required between two non-co-located       │
│  travel events.                                         │
│  [  3  ] days                                           │
│                                                         │
│  Co-location Radius                                     │
│  Locations within this radius are considered the        │
│  same area (exempt from travel buffer).                 │
│  [  10  ] miles                                         │
│                                                         │
│  Performer Ceiling                                      │
│  Number of confirmed performers that maps to a          │
│  100% score on the Performer Lineup dimension.          │
│  [  5  ] performers                                     │
│                                                         │
│                                   [Reset Defaults]      │
└─────────────────────────────────────────────────────────┘
```

**Backend Storage:** New config category `conflict_rules` with keys:
- `distance_threshold_miles` (integer, default: 50)
- `consecutive_window_days` (integer, default: 1)
- `travel_buffer_days` (integer, default: 3)
- `colocation_radius_miles` (integer, default: 10)
- `performer_ceiling` (integer, default: 5)

---

## Technical Architecture

### Backend: Conflict Detection Service

**New file:** `backend/src/services/conflict_service.py`

```
ConflictService
├── detect_conflicts(team_id, start_date, end_date) → ConflictGroupList
│   ├── _find_time_overlaps(events) → List[ConflictEdge]
│   ├── _find_distance_conflicts(events, threshold, window) → List[ConflictEdge]
│   ├── _find_travel_buffer_violations(events, buffer_days, colocation_radius) → List[ConflictEdge]
│   └── _build_conflict_groups(edges) → List[ConflictGroup]
├── score_event(event_detail) → EventScores
│   ├── _score_venue_quality(location) → float
│   ├── _score_organizer_reputation(organizer) → float
│   ├── _score_performer_lineup(performers, ceiling) → float
│   ├── _score_logistics_ease(event) → float
│   └── _score_readiness(event) → float
└── compute_composite(scores, weights) → float
```

**Haversine implementation:** Pure Python in `backend/src/services/geo_utils.py`. No external geo library needed — the haversine formula is ~10 lines. Coordinates come from `Location.latitude` and `Location.longitude` which are already `Numeric(10,7)`.

### Backend: New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/events/conflicts` | Detect conflicts for a date range. Returns conflict groups with scored events. |
| `GET` | `/api/events/{guid}/score` | Get quality scores for a single event. |
| `POST` | `/api/events/conflicts/resolve` | Batch-resolve a conflict group (set attendance on selected events). |
| `GET` | `/api/config/conflict_rules` | Get conflict rule settings. |
| `PUT` | `/api/config/conflict_rules` | Update conflict rule settings. |

**Conflict Detection Endpoint Detail:**

```
GET /api/events/conflicts?start_date=2026-02-01&end_date=2026-04-30

Response:
{
  "conflict_groups": [
    {
      "group_id": "cg_1",
      "status": "unresolved",
      "events": [
        {
          "guid": "evt_...",
          "title": "Concert X",
          "event_date": "2026-02-08",
          "scores": {
            "venue_quality": 80,
            "organizer_reputation": 90,
            "performer_lineup": 60,
            "logistics_ease": 67,
            "readiness": 100,
            "composite": 78
          },
          "attendance": "planned"
        },
        {
          "guid": "evt_...",
          "title": "Festival Y",
          "event_date": "2026-02-08",
          "scores": { ... },
          "attendance": "planned"
        }
      ],
      "edges": [
        {
          "event_a_guid": "evt_...",
          "event_b_guid": "evt_...",
          "conflict_type": "time_overlap",
          "detail": "Both events: 14:00–18:00 on Feb 8"
        }
      ]
    }
  ],
  "summary": {
    "total_groups": 3,
    "unresolved": 2,
    "partially_resolved": 1,
    "resolved": 0
  }
}
```

### Frontend: New Components

| Component | Location | Description |
|-----------|----------|-------------|
| `ConflictBadge` | `components/events/ConflictBadge.tsx` | Amber warning badge for event cards and calendar cells. |
| `ConflictResolutionPanel` | `components/events/ConflictResolutionPanel.tsx` | Conflict group cards with quick-resolve actions. |
| `RadarComparisonDialog` | `components/events/RadarComparisonDialog.tsx` | Side-by-side radar chart comparison of 2+ events. |
| `EventRadarChart` | `components/events/EventRadarChart.tsx` | Single-event radar chart (reusable). |
| `TimelinePlanner` | `components/events/TimelinePlanner.tsx` | Scrollable timeline view with score bars and conflict connectors. |
| `TimelineEventMarker` | `components/events/TimelineEventMarker.tsx` | Individual event row in the timeline with score bar and dimension segments. |
| `DimensionMicroBar` | `components/events/DimensionMicroBar.tsx` | Linearized radar: segmented micro-bar showing individual dimension scores. |
| `ConflictRulesSection` | `components/settings/ConflictRulesSection.tsx` | Settings form for conflict detection thresholds. |

### Frontend: New Hooks

| Hook | Description |
|------|-------------|
| `useConflicts(startDate, endDate)` | Fetches conflict groups for a date range. |
| `useEventScore(guid)` | Fetches quality scores for a single event. |
| `useConflictRules()` | CRUD for conflict rule settings. |
| `useResolveConflict()` | Mutation hook for resolving conflict groups. |

### Frontend: New API Contracts

**New file:** `frontend/src/contracts/api/conflict-api.ts`

```typescript
// Conflict types
export type ConflictType = 'time_overlap' | 'distance' | 'travel_buffer'
export type ConflictGroupStatus = 'unresolved' | 'partially_resolved' | 'resolved'

// Scoring
export interface EventScores {
  venue_quality: number        // 0–100
  organizer_reputation: number // 0–100
  performer_lineup: number     // 0–100
  logistics_ease: number       // 0–100
  readiness: number            // 0–100
  composite: number            // 0–100 weighted average
}

export interface ScoredEvent {
  guid: string
  title: string
  event_date: string
  start_time: string | null
  end_time: string | null
  is_all_day: boolean
  category: CategorySummary | null
  location: LocationSummary | null
  organizer: OrganizerSummary | null
  performer_count: number
  travel_required: boolean | null
  attendance: AttendanceStatus
  scores: EventScores
}

// Conflict edges
export interface ConflictEdge {
  event_a_guid: string
  event_b_guid: string
  conflict_type: ConflictType
  detail: string              // Human-readable description
}

// Conflict groups
export interface ConflictGroup {
  group_id: string
  status: ConflictGroupStatus
  events: ScoredEvent[]
  edges: ConflictEdge[]
}

// API responses
export interface ConflictDetectionResponse {
  conflict_groups: ConflictGroup[]
  summary: {
    total_groups: number
    unresolved: number
    partially_resolved: number
    resolved: number
  }
}

export interface ConflictResolveRequest {
  group_id: string
  decisions: Array<{
    event_guid: string
    attendance: 'planned' | 'skipped'
  }>
}

// Settings
export interface ConflictRulesConfig {
  distance_threshold_miles: number
  consecutive_window_days: number
  travel_buffer_days: number
  colocation_radius_miles: number
  performer_ceiling: number
}
```

---

## Data Requirements

### Existing Data (No Changes)

- **Event model**: `event_date`, `start_time`, `end_time`, `is_all_day`, `travel_required`, `ticket_required`, `timeoff_required`, `ticket_status`, `timeoff_status`, `travel_status`, `attendance` — all already present.
- **Location model**: `latitude`, `longitude`, `rating` — already present with geocoding support.
- **Organizer model**: `rating` — already present.
- **Performer model**: `EventPerformer.status` — already present for confirmed/announced/cancelled tracking.

### New Data

- **Config entries**: 5 new entries in the `conflict_rules` config category (see Settings section). Stored in the existing `configurations` table.
- **No new database tables**: Conflict groups are computed at query time, not persisted. This keeps the model simple and avoids stale conflict data when events change.
- **No schema migrations**: All new data fits in the existing `configurations` table structure.

### Performance Considerations

- **Conflict detection is O(n^2)** in the worst case (comparing all event pairs). For the expected cardinality (hundreds of events per team per quarter), this is well within acceptable limits.
- **Caching**: The conflict detection response for a given date range can be cached on the frontend for the session. Any event mutation (create/update/delete) invalidates the cache for overlapping date ranges.
- **Lazy loading**: The Timeline Planner loads events in monthly chunks as the user scrolls, avoiding loading an entire year upfront.

---

## Phased Delivery

### Phase 1: Foundation — Conflict Detection & Settings

**Scope:**
- Conflict Rules settings section in the Settings page
- Backend conflict detection service (all 3 conflict types)
- Backend scoring service (all 5 initial dimensions)
- `GET /api/events/conflicts` endpoint
- `GET /api/events/{guid}/score` endpoint
- Haversine geo utility

**Deliverables:**
- ConflictRulesSection component
- conflict_service.py, geo_utils.py
- API endpoints with tests
- Config category registration

### Phase 2: Calendar Conflict Indicators & Resolution Panel

**Scope:**
- Conflict badges on calendar cells and event cards
- Conflict tab in day detail dialog
- Conflict resolution panel with quick-resolve actions
- `POST /api/events/conflicts/resolve` endpoint

**Deliverables:**
- ConflictBadge component
- ConflictResolutionPanel component
- useConflicts hook
- Calendar cell and EventCard modifications
- Day detail dialog Conflicts tab

### Phase 3: Radar Chart Comparison

**Scope:**
- Single-event radar chart component
- Side-by-side comparison dialog for conflict groups
- Dimension breakdown table
- Event detail side-by-side summary

**Deliverables:**
- EventRadarChart component (Recharts RadarChart)
- RadarComparisonDialog component
- useEventScore hook
- Integration with ConflictResolutionPanel "Compare" action

### Phase 4: Timeline Planner View

**Scope:**
- Timeline Planner tab on Events page
- Scrollable chronological timeline with score bars
- Dimension micro-bars (linearized radar)
- Conflict connectors between related events
- Inline expand to radar chart
- Filters: date range, category, conflicts-only, unresolved-only

**Deliverables:**
- TimelinePlanner component
- TimelineEventMarker component
- DimensionMicroBar component
- EventsPage tab integration
- Mobile adaptation (bottom sheet, simplified markers)

### Phase 5: KPI Integration & Polish

**Scope:**
- TopHeader stats for Planner view: "Conflicts", "Unresolved", "Events Scored", "Avg Quality"
- Notification integration: notify when new conflicts are detected after event creation
- Keyboard navigation for timeline
- Performance optimization (virtual scrolling for large timelines)

**Deliverables:**
- Updated useEventStats or new usePlannerStats hook
- Notification trigger on conflict creation
- Accessibility improvements
- Performance tuning

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Conflict detection accuracy | 100% of time overlaps, >95% of distance conflicts (requires geocoded locations) | Automated test suite with fixture events |
| Conflict resolution rate | >70% of detected conflict groups resolved within 7 days | Backend query on conflict group resolution timestamps |
| Planner adoption | >40% of active users visit the Planner view within first month | Frontend analytics (page view tracking) |
| Scoring coverage | >80% of upcoming events have a composite score (requires location + organizer data) | Backend stats endpoint |

---

## Open Questions

1. **Dimension weights**: Should users be able to customize dimension weights in v1, or is equal weighting sufficient for the initial release? (Recommendation: equal weights for v1, configurable weights as a fast-follow.)

2. **Historical scoring dimension**: When past event analysis results (PhotoStats scores) are available, how should they influence the event score? (Recommendation: defer to a follow-up PRD once the base scoring framework is proven.)

3. **Conflict notifications**: Should conflict detection run automatically on event creation and push a notification, or only on-demand when the user opens the Planner? (Recommendation: on-demand for v1 to keep the backend simple; async detection as a Phase 5 enhancement.)

4. **Series-level conflicts**: If Event A conflicts with Event B[2/5] (part of a series), should the entire series be flagged? (Recommendation: flag only the individual series event that conflicts, not the whole series.)

5. **Unit preference**: Should the distance threshold support both miles and kilometers? (Recommendation: support a unit toggle in Settings; store internally in miles and convert for display.)

---

## Appendix A: Haversine Formula Reference

```python
import math

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in miles."""
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))
```

## Appendix B: Recharts RadarChart Integration

The project already depends on Recharts 2.15.0. The `RadarChart` component is part of Recharts and requires no additional dependencies:

```tsx
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, ResponsiveContainer } from 'recharts'

// Data format for overlaid comparison:
const dimensions = [
  { dimension: 'Venue Quality', eventA: 80, eventB: 60 },
  { dimension: 'Organizer Rep.', eventA: 90, eventB: 80 },
  { dimension: 'Performers', eventA: 60, eventB: 40 },
  { dimension: 'Logistics Ease', eventA: 67, eventB: 33 },
  { dimension: 'Readiness', eventA: 100, eventB: 67 },
]
```

Chart colors should use the existing `CHART_COLORS` from the trend components, mapped through CSS variables for dark theme compliance.

## Appendix C: Linearized Radar Chart (Dimension Micro-Bar)

The "linearized radar" concept projects the multi-dimensional spider web into a single horizontal bar:

```
Full bar width = composite score (0–100% of container)
├─ Segment 1: Venue Quality    (color: chart-1, width proportional to score)
├─ Segment 2: Organizer Rep.   (color: chart-2, width proportional to score)
├─ Segment 3: Performers       (color: chart-3, width proportional to score)
├─ Segment 4: Logistics Ease   (color: chart-4, width proportional to score)
└─ Segment 5: Readiness        (color: chart-5, width proportional to score)
```

Each segment's width = `(dimension_score / total_of_all_scores) * composite_bar_width`

This gives users a quick visual fingerprint of _why_ an event scores the way it does: a bar dominated by chart-1 color means venue quality is the main strength; a bar with even segments means the event is balanced.

On hover, each segment expands to show: `"Venue Quality: 80/100"`.
