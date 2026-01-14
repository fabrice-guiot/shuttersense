# Research: Event Deadline Calendar Display

**Feature**: 018-event-deadline-calendar
**Date**: 2026-01-14

## Research Questions

### 1. Deadline Entry Storage Strategy

**Question**: How should deadline entries be stored - as Event records with a type marker, or in a separate table?

**Decision**: Store as Event records with `is_deadline=True` boolean field

**Rationale**:
- Deadline entries naturally appear in Events API without additional queries
- Calendar views work automatically - no special handling needed
- Uses existing Event infrastructure (GUIDs, timestamps, soft delete)
- Series relationship already exists (`series_id` foreign key)
- Simpler than maintaining a separate table with duplicate logic

**Alternatives Considered**:
1. **Separate DeadlineEntry table**: Would require duplicate query logic, separate API endpoints, and custom calendar integration. Rejected for complexity.
2. **Computed/Virtual entries**: Generate deadline entries on-the-fly in API responses. Rejected because it makes pagination/filtering complex and breaks consistency.
3. **Event type enum instead of boolean**: Using `event_type: 'event' | 'deadline'` instead of `is_deadline: boolean`. Could work, but boolean is simpler for this binary distinction.

---

### 2. EventSeries Deadline Fields Migration

**Question**: How should deadline fields be added to EventSeries model?

**Decision**: Add `deadline_date` (Date, nullable) and `deadline_time` (Time, nullable) columns to event_series table via Alembic migration

**Rationale**:
- Matches existing pattern for Date/Time fields in Event model
- Separate date and time fields allow flexible deadline specification
- Nullable because deadline is optional
- No default value needed - NULL means no deadline

**Migration Approach**:
```python
# New migration: add_deadline_to_event_series.py
op.add_column('event_series', sa.Column('deadline_date', sa.Date(), nullable=True))
op.add_column('event_series', sa.Column('deadline_time', sa.Time(), nullable=True))
```

**Note**: Existing `deadline_date` field on Event model is for individual event deadlines. Series-level deadline is a new concept that creates derived deadline entries.

---

### 3. Deadline Entry Synchronization Logic

**Question**: How should deadline entries be automatically created/updated/deleted when EventSeries deadline changes?

**Decision**: Implement synchronization in EventService with explicit methods called during EventSeries CRUD operations

**Implementation Approach**:
1. **On EventSeries create with deadline**: Create deadline Event entry
2. **On EventSeries update with deadline change**:
   - If deadline added: Create deadline entry
   - If deadline modified: Update deadline entry (date, time)
   - If deadline removed: Delete deadline entry
3. **On EventSeries delete**: Cascade deletes deadline entry (via `series_id` FK with CASCADE)

**Synchronization Logic** (in EventService):
```python
def _sync_deadline_entry(self, series: EventSeries) -> None:
    """Synchronize deadline entry for an EventSeries."""
    existing = self._get_deadline_entry(series.id)

    if series.deadline_date and not existing:
        # Create deadline entry
        self._create_deadline_entry(series)
    elif series.deadline_date and existing:
        # Update deadline entry
        self._update_deadline_entry(existing, series)
    elif not series.deadline_date and existing:
        # Delete deadline entry
        self._delete_deadline_entry(existing)
```

**Rationale**:
- Explicit method calls are testable and traceable
- No database triggers (keeps logic in Python)
- CASCADE delete handles series deletion automatically

---

### 4. API Protection for Deadline Entries

**Question**: How should the API prevent direct modification of deadline entries?

**Decision**: Add validation at API layer that rejects operations on deadline entries with clear error messages

**Implementation**:
```python
# In events.py API endpoints

@router.patch("/events/{guid}")
def update_event(guid: str, update: EventUpdate):
    event = event_service.get_by_guid(guid)
    if event.is_deadline:
        raise HTTPException(
            status_code=403,
            detail="Deadline entries cannot be modified directly. Update the deadline on the parent Event Series instead."
        )
    # ... proceed with update

@router.delete("/events/{guid}")
def delete_event(guid: str):
    event = event_service.get_by_guid(guid)
    if event.is_deadline:
        raise HTTPException(
            status_code=403,
            detail="Deadline entries cannot be deleted directly. Remove the deadline from the parent Event Series instead."
        )
    # ... proceed with delete
```

**Error Response Format**:
```json
{
  "detail": "Deadline entries cannot be modified directly. Update the deadline on the parent Event Series instead.",
  "series_guid": "ser_01hgw2bbg0000000000000001"
}
```

**Rationale**:
- HTTP 403 Forbidden is appropriate (user authenticated but action not allowed)
- Clear message tells user what to do instead
- Include series_guid to help user navigate to the right place

---

### 5. Frontend Deadline Styling

**Question**: How should deadline entries be visually distinguished in the calendar?

**Decision**: Use existing EventCard with conditional styling based on `is_deadline` flag

**Visual Design**:
- **Color**: Red (`destructive` color token from design system)
- **Icon**: ClockAlert from Lucide icons
- **Title format**: "[Deadline] {Series Title}"
- **Additional indicators**: No location, no performers (as per spec)

**Implementation in EventCard.tsx**:
```tsx
// Detect deadline entry
const isDeadline = event.is_deadline ?? false

// Apply conditional styling
const borderColor = isDeadline
  ? 'border-l-destructive'
  : getAttendanceColor(event.attendance)

// Show deadline icon
{isDeadline && <ClockAlert className="h-4 w-4 text-destructive" />}

// Title with prefix (handled by backend - title already includes "[Deadline]")
```

**Design Token Usage**:
- `text-destructive` for icon and text
- `border-l-destructive` for left border (replaces attendance color)
- `bg-destructive/10` for hover state background

**Rationale**:
- Follows existing design system conventions
- Red/destructive color universally signals urgency/deadlines
- ClockAlert icon clearly communicates time-sensitive nature
- Reuses EventCard component - no new component needed

---

### 6. Deadline Entry Data Model

**Question**: What fields should a deadline entry Event record have?

**Decision**: Deadline entries are Event records with specific field values:

| Field | Value | Notes |
|-------|-------|-------|
| `is_deadline` | `True` | New field - distinguishes from regular events |
| `title` | `"[Deadline] {Series.title}"` | Prefixed automatically |
| `event_date` | `Series.deadline_date` | Synced from series |
| `start_time` | `Series.deadline_time` | Synced from series |
| `end_time` | `Series.deadline_time` | Same as start (point-in-time) |
| `series_id` | `Series.id` | Links to parent series |
| `sequence_number` | `NULL` | Not part of event sequence |
| `category_id` | `NULL` | Inherits from series |
| `location_id` | `NULL` | Always null per spec |
| `organizer_id` | `Series.organizer_id` | Inherits from series |
| `status` | `'future'` | Default status |
| `attendance` | `NULL` | Not applicable |
| `is_all_day` | `False` if time set, `True` otherwise | Based on deadline_time |

**Rationale**:
- Minimal required fields reduces maintenance burden
- NULL values indicate "not applicable" for deadline entries
- Sequence number NULL distinguishes from numbered series events
- Title prefixed by backend ensures consistency

---

### 7. Read-Only View in Frontend

**Question**: How should the UI present deadline entries when clicked?

**Decision**: Show a read-only detail view with link to parent EventSeries

**UI Elements**:
1. Read-only event detail panel (existing EventDetail component)
2. Prominent notice: "This is a deadline entry. To modify, edit the parent Event Series."
3. Link/button to navigate to EventSeries edit view
4. Hide edit/delete buttons entirely

**Implementation**:
```tsx
// In EventDetail or EventForm component
{event.is_deadline && (
  <Alert variant="info">
    <ClockAlert className="h-4 w-4" />
    <AlertDescription>
      This is a deadline entry for{' '}
      <Link to={`/events/series/${event.series_guid}`}>
        {event.series_title}
      </Link>
      . To modify the deadline, edit the Event Series.
    </AlertDescription>
  </Alert>
)}
```

**Rationale**:
- Clear communication prevents user confusion
- Direct link reduces friction for legitimate edits
- Hiding buttons prevents accidental clicks (cleaner than disabled buttons)

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Storage | Event records with `is_deadline=True` |
| EventSeries fields | `deadline_date` (Date), `deadline_time` (Time) |
| Synchronization | Service-layer methods in EventService |
| API protection | 403 Forbidden with helpful error messages |
| Frontend styling | Red/destructive color, ClockAlert icon |
| Read-only view | Alert with link to parent EventSeries |

## Dependencies Identified

1. **New migration**: Add deadline fields to event_series table
2. **New migration**: Add is_deadline field to events table
3. **EventService extension**: Deadline sync methods
4. **API validation**: Protection middleware for deadline entries
5. **Frontend types**: Add is_deadline to Event interface
6. **EventCard update**: Conditional deadline styling

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Deadline entry orphaned if sync fails | Wrap sync in transaction; add cleanup job for orphans |
| Existing API consumers confused by is_deadline | Default to not filtering - deadline entries appear like regular events |
| Performance impact on series operations | Deadline sync is single record operation - negligible impact |
