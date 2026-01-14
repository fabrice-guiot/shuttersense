# Data Model: Event Deadline Calendar Display

**Feature**: 018-event-deadline-calendar
**Date**: 2026-01-14

## Entity Changes

### EventSeries (Extended)

Add two new fields to the existing EventSeries model:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `deadline_date` | Date | Yes | NULL | Series-level deadline date for deliverables |
| `deadline_time` | Time | Yes | NULL | Optional deadline time (e.g., 11:59 PM for competitions) |

**Validation Rules**:
- `deadline_date`: Any valid date (no restriction relative to event dates)
- `deadline_time`: Valid time in 24-hour format, only meaningful if `deadline_date` is set

**Behavior**:
- When `deadline_date` is set, triggers creation of associated deadline entry
- When `deadline_date` is updated, triggers update of deadline entry
- When `deadline_date` is cleared (set to NULL), triggers deletion of deadline entry

### Event (Extended)

Add one new field to the existing Event model:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `is_deadline` | Boolean | No | False | True if this event represents a deadline entry |

**Validation Rules**:
- `is_deadline`: Cannot be set to True via API create/update operations (system-managed only)

**Behavior**:
- Events with `is_deadline=True` are protected from direct modification
- Deadline events automatically deleted when parent series is deleted (CASCADE)

## Entity Relationships

```text
┌─────────────────────────────────────────────────────────┐
│                     EventSeries                          │
├─────────────────────────────────────────────────────────┤
│ id (PK)                                                  │
│ uuid (UUIDv7) → guid: ser_XXXXX                         │
│ title                                                    │
│ description                                              │
│ category_id (FK) ─────────────────────────┐             │
│ location_id (FK) ──────────────────────┐  │             │
│ organizer_id (FK) ─────────────────┐   │  │             │
│ input_timezone                      │   │  │             │
│ ticket_required                     │   │  │             │
│ timeoff_required                    │   │  │             │
│ travel_required                     │   │  │             │
│ total_events                        │   │  │             │
│ deadline_date (NEW)                 │   │  │             │
│ deadline_time (NEW)                 │   │  │             │
│ created_at, updated_at              │   │  │             │
└─────────────────────────────────────│───│──│─────────────┘
         │                            │   │  │
         │ 1:N                        │   │  │
         ▼                            │   │  │
┌─────────────────────────────────────│───│──│─────────────┐
│                       Event         │   │  │             │
├─────────────────────────────────────│───│──│─────────────┤
│ id (PK)                             │   │  │             │
│ uuid (UUIDv7) → guid: evt_XXXXX     │   │  │             │
│ title                               │   │  │             │
│ description                         │   │  │             │
│ event_date                          │   │  │             │
│ start_time, end_time                │   │  │             │
│ is_all_day                          │   │  │             │
│ input_timezone                      │   │  │             │
│ series_id (FK) ────────────────────────────┘             │
│ sequence_number                     │   │  │             │
│ category_id (FK) ───────────────────│───│──┘             │
│ location_id (FK) ───────────────────│───┘                │
│ organizer_id (FK) ──────────────────┘                    │
│ status, attendance                                       │
│ ticket_*, timeoff_*, travel_*                           │
│ deadline_date (individual event)                         │
│ is_deadline (NEW) ◄── True for deadline entries         │
│ deleted_at                                               │
│ created_at, updated_at                                   │
└──────────────────────────────────────────────────────────┘
```

## Deadline Entry Composition

When a deadline entry is created, it derives its values from the parent EventSeries:

| Deadline Entry Field | Source | Notes |
|---------------------|--------|-------|
| `uuid` | Generated | New UUIDv7, guid prefix `evt_` |
| `title` | `"[Deadline] " + series.title` | Prefixed |
| `event_date` | `series.deadline_date` | Direct copy |
| `start_time` | `series.deadline_time` | Direct copy |
| `end_time` | `series.deadline_time` | Same as start |
| `is_all_day` | `series.deadline_time is NULL` | True if no time |
| `input_timezone` | `series.input_timezone` | Direct copy |
| `series_id` | `series.id` | FK relationship |
| `sequence_number` | `NULL` | Not sequenced |
| `category_id` | `NULL` | Inherits from series |
| `location_id` | `NULL` | Never set |
| `organizer_id` | `series.organizer_id` | Direct copy |
| `status` | `'future'` | Default |
| `attendance` | `NULL` | Not applicable |
| `is_deadline` | `True` | Distinguishing flag |
| `ticket_required` | `NULL` | Not applicable |
| `timeoff_required` | `NULL` | Not applicable |
| `travel_required` | `NULL` | Not applicable |

## State Transitions

### Deadline Entry Lifecycle

```text
                    ┌────────────────┐
                    │  No Deadline   │
                    │  (series has   │
                    │  no deadline   │
                    │  date set)     │
                    └───────┬────────┘
                            │
                            │ Set deadline_date
                            │ on EventSeries
                            ▼
                    ┌────────────────┐
     Update         │  Deadline      │
     deadline  ◄────│  Entry         │────► Delete
     date/time      │  Exists        │      deadline_date
        │           └───────┬────────┘      on EventSeries
        │                   │                      │
        │                   │ Delete               │
        │                   │ EventSeries          │
        └───────────────────┼──────────────────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │  Deadline      │
                    │  Entry         │
                    │  Deleted       │
                    └────────────────┘
```

## Database Migration

### Migration: Add deadline fields to event_series

```sql
-- Add deadline_date column
ALTER TABLE event_series
ADD COLUMN deadline_date DATE NULL;

-- Add deadline_time column
ALTER TABLE event_series
ADD COLUMN deadline_time TIME NULL;
```

### Migration: Add is_deadline to events

```sql
-- Add is_deadline column with default
ALTER TABLE events
ADD COLUMN is_deadline BOOLEAN NOT NULL DEFAULT FALSE;

-- Add index for filtering deadline entries
CREATE INDEX idx_events_is_deadline
ON events (is_deadline)
WHERE is_deadline = TRUE;
```

## Query Patterns

### Get all events (including deadlines) for calendar

```sql
SELECT e.*, es.title as series_title
FROM events e
LEFT JOIN event_series es ON e.series_id = es.id
WHERE e.event_date BETWEEN :start_date AND :end_date
  AND e.deleted_at IS NULL
ORDER BY e.event_date, e.start_time;
```

### Get deadline entry for a series

```sql
SELECT * FROM events
WHERE series_id = :series_id
  AND is_deadline = TRUE
  AND deleted_at IS NULL;
```

### Filter out deadline entries (if needed)

```sql
SELECT * FROM events
WHERE event_date BETWEEN :start_date AND :end_date
  AND deleted_at IS NULL
  AND is_deadline = FALSE;  -- Exclude deadlines
```

## Indexing Strategy

| Index | Columns | Condition | Purpose |
|-------|---------|-----------|---------|
| `idx_events_is_deadline` | `is_deadline` | `WHERE is_deadline = TRUE` | Quickly find deadline entries |
| `idx_events_series_deadline` | `series_id, is_deadline` | None | Find deadline for specific series |

**Note**: Existing indexes on `event_date` and `series_id` remain sufficient for primary query patterns.
