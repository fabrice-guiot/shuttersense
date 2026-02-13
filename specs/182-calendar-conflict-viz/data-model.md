# Data Model: Calendar Conflict Visualization & Event Picker

**Feature Branch**: `182-calendar-conflict-viz`
**Created**: 2026-02-13

## Overview

This feature introduces **no new database tables**. All new data is stored in the existing `configurations` table (10 new entries per team). Conflict groups and event scores are computed at query time from existing event, location, organizer, and performer data.

---

## Existing Entities (Referenced, Not Modified)

### Event (table: `events`)

Key fields used by conflict detection and scoring:

| Field | Type | Used For |
|-------|------|----------|
| `event_date` | Date, NOT NULL | Time overlap + distance + travel buffer detection |
| `start_time` | Time, nullable | Time overlap detection |
| `end_time` | Time, nullable | Time overlap detection |
| `is_all_day` | Boolean, default=False | Time overlap (all-day conflicts with everything on same date) |
| `location_id` | FK → locations | Distance conflict detection (via location coordinates) |
| `organizer_id` | FK → organizers | Organizer Reputation scoring (via organizer rating) |
| `travel_required` | Boolean, nullable | Travel buffer detection + Logistics Ease scoring |
| `ticket_required` | Boolean, nullable | Logistics Ease scoring |
| `timeoff_required` | Boolean, nullable | Logistics Ease scoring |
| `ticket_status` | String(50), nullable | Readiness scoring |
| `timeoff_status` | String(50), nullable | Readiness scoring |
| `travel_status` | String(50), nullable | Readiness scoring |
| `attendance` | String(50), default="planned" | Conflict resolution status derivation |
| `team_id` | FK → teams | Tenant isolation |

### Location (table: `locations`)

| Field | Type | Used For |
|-------|------|----------|
| `latitude` | Numeric(10,7), nullable | Haversine distance calculation |
| `longitude` | Numeric(10,7), nullable | Haversine distance calculation |
| `rating` | Integer, nullable (1–5) | Venue Quality scoring |

### Organizer (table: `organizers`)

| Field | Type | Used For |
|-------|------|----------|
| `rating` | Integer, nullable (1–5) | Organizer Reputation scoring |

### EventPerformer (table: `event_performers`)

| Field | Type | Used For |
|-------|------|----------|
| `status` | String(50), default="announced" | Performer Lineup scoring (count where status='confirmed') |

---

## New Configuration Entries (table: `configurations`)

All entries use the existing `configurations` table structure:

```
(team_id, category, key, value_json, description, source, created_by_user_id, updated_by_user_id)
```

### Category: `conflict_rules`

| Key | Default Value | Description |
|-----|---------------|-------------|
| `distance_threshold_miles` | `{"value": 50, "label": "Distance Threshold (miles)"}` | Maximum miles between events before flagging a distance conflict |
| `consecutive_window_days` | `{"value": 1, "label": "Consecutive Window (days)"}` | Number of days forward to check for distance conflicts (0 = same-day only) |
| `travel_buffer_days` | `{"value": 3, "label": "Travel Buffer (days)"}` | Minimum days between two non-co-located travel events |
| `colocation_radius_miles` | `{"value": 10, "label": "Co-location Radius (miles)"}` | Two locations within this radius are considered co-located |
| `performer_ceiling` | `{"value": 5, "label": "Performer Ceiling"}` | Confirmed performer count that maps to 100% on Performer Lineup dimension |

### Category: `scoring_weights`

| Key | Default Value | Description |
|-----|---------------|-------------|
| `weight_venue_quality` | `{"value": 20, "label": "Venue Quality"}` | Weight for Venue Quality dimension in composite score |
| `weight_organizer_reputation` | `{"value": 20, "label": "Organizer Reputation"}` | Weight for Organizer Reputation dimension |
| `weight_performer_lineup` | `{"value": 20, "label": "Performer Lineup"}` | Weight for Performer Lineup dimension |
| `weight_logistics_ease` | `{"value": 20, "label": "Logistics Ease"}` | Weight for Logistics Ease dimension |
| `weight_readiness` | `{"value": 20, "label": "Readiness"}` | Weight for Readiness dimension |

---

## Computed Entities (Not Persisted)

### Conflict Group

Computed at query time. Represents a connected component in the event-conflict graph.

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | String | Ephemeral identifier (e.g., `cg_1`, `cg_2`) — generated per query, not persisted |
| `status` | Enum: `unresolved` / `partially_resolved` / `resolved` | Derived from member events' `attendance` values |
| `events` | List[ScoredEvent] | Member events with their quality scores |
| `edges` | List[ConflictEdge] | Pairwise conflict relationships with type and detail |

**Resolution status derivation**:
- `resolved`: At most 1 event has `attendance ∈ {planned, attended}`
- `partially_resolved`: More than 1 but fewer than all events have `attendance ∈ {planned, attended}`
- `unresolved`: All events have `attendance = planned`

### Conflict Edge

| Field | Type | Description |
|-------|------|-------------|
| `event_a_guid` | String | GUID of first event |
| `event_b_guid` | String | GUID of second event |
| `conflict_type` | Enum: `time_overlap` / `distance` / `travel_buffer` | Type of conflict |
| `detail` | String | Human-readable description (e.g., "Both events: 14:00–18:00 on Feb 8") |

### Event Scores

| Field | Type | Description |
|-------|------|-------------|
| `venue_quality` | Float (0–100) | `location.rating * 20` (null → 50) |
| `organizer_reputation` | Float (0–100) | `organizer.rating * 20` (null → 50) |
| `performer_lineup` | Float (0–100) | `min(confirmed_count / ceiling, 1.0) * 100` |
| `logistics_ease` | Float (0–100) | Each not-required item → +33.3 |
| `readiness` | Float (0–100) | Each resolved required item → proportional share of 100 |
| `composite` | Float (0–100) | Weighted average using team's scoring weights |

---

## Scoring Logic Detail

### Venue Quality
```
if location is None or location.rating is None:
    score = 50  # neutral default
else:
    score = location.rating * 20  # 1→20, 2→40, 3→60, 4→80, 5→100
```

### Organizer Reputation
```
if organizer is None or organizer.rating is None:
    score = 50  # neutral default
else:
    score = organizer.rating * 20  # 1→20, 2→40, 3→60, 4→80, 5→100
```

### Performer Lineup
```
confirmed_count = count of event_performers where status = 'confirmed'
ceiling = config.performer_ceiling (default: 5)
score = min(confirmed_count / ceiling, 1.0) * 100
```

### Logistics Ease
```
items = [travel_required, timeoff_required, ticket_required]
easy_count = count of items where value is False or None
score = (easy_count / 3) * 100
# All false/null → 100, all true → 0
```

### Readiness
```
required_items = []
if ticket_required:  required_items.append(ticket_status in ['ready'])
if timeoff_required: required_items.append(timeoff_status in ['approved'])
if travel_required:  required_items.append(travel_status in ['booked'])

if len(required_items) == 0:
    score = 100  # nothing required = fully ready
else:
    score = (count of True in required_items / len(required_items)) * 100
```

### Composite Score
```
weights = team's scoring_weights config
dimensions = [venue_quality, organizer_reputation, performer_lineup, logistics_ease, readiness]
weight_keys = [weight_venue_quality, weight_organizer_reputation, weight_performer_lineup, weight_logistics_ease, weight_readiness]

total_weight = sum(w for w in weights if w > 0)
if total_weight == 0:
    composite = 0
else:
    composite = sum(dim * weight for dim, weight in zip(dimensions, weights)) / total_weight
```

---

## Conflict Detection Logic

### Time Overlap
```
For each pair (A, B) where A.event_date == B.event_date:
    if A.is_all_day or B.is_all_day:
        → conflict (all-day conflicts with everything on same date)
    elif A.start_time is None or A.end_time is None or B.start_time is None or B.end_time is None:
        → conflict (conservative: missing times on same date = potential overlap)
    elif A.start_time < B.end_time and B.start_time < A.end_time:
        → conflict (standard interval overlap)
```

### Distance Conflict
```
For each pair (A, B) where:
    abs(A.event_date - B.event_date) <= consecutive_window_days
    AND A.location has coordinates
    AND B.location has coordinates:

    distance = haversine(A.location, B.location)
    if distance > distance_threshold_miles:
        → conflict
```

### Travel Buffer Violation
```
For each pair (A, B) where:
    A.travel_required == True
    AND B.travel_required == True
    AND A.location has coordinates
    AND B.location has coordinates
    AND haversine(A.location, B.location) > colocation_radius_miles:

    days_between = abs(A.event_date - B.event_date)
    if days_between < travel_buffer_days:
        → conflict
```

### Group Construction (Union-Find)
```
edges = time_overlap_edges + distance_edges + travel_buffer_edges
groups = connected_components(edges)  # Union-Find algorithm
For each group:
    derive status from member events' attendance values
    assign ephemeral group_id (cg_1, cg_2, ...)
```

---

## Data Migration

### Alembic Migration: Seed Defaults for Existing Teams

Follows the pattern from migrations `019`, `043`, `050`:

```
For each team in teams table:
    For each config in DEFAULT_CONFLICT_RULES + DEFAULT_SCORING_WEIGHTS:
        If not exists (team_id, category, key):
            INSERT into configurations
```

Uses raw SQL via `sa.sql.table()` and `sa.sql.column()` for migration compatibility.
