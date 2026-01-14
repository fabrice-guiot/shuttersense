# Quickstart: Event Deadline Calendar Display

**Feature**: 018-event-deadline-calendar
**Date**: 2026-01-14

## Overview

This feature adds deadline visibility to the calendar by automatically creating "deadline entries" when an Event Series has a deadline date set. Deadline entries appear as distinct events with red styling and are protected from direct modification.

## Key Concepts

### Deadline Entry
A deadline entry is an Event record with `is_deadline=True`. It:
- Appears in the calendar on the deadline date
- Shows "[Deadline] {Series Title}" as its title
- Uses red color and ClockAlert icon
- Is protected from direct edit/delete
- Automatically syncs with parent EventSeries deadline

### Series-Level Deadline
Deadline is a property of EventSeries, not individual Events:
- One deadline per series
- Applies to all events in the series
- Changes via EventSeries API only

## Implementation Steps

### 1. Database Migrations

**Add deadline fields to event_series:**
```python
# backend/src/db/migrations/versions/XXX_add_deadline_to_series.py
def upgrade():
    op.add_column('event_series', sa.Column('deadline_date', sa.Date(), nullable=True))
    op.add_column('event_series', sa.Column('deadline_time', sa.Time(), nullable=True))
```

**Add is_deadline to events:**
```python
# backend/src/db/migrations/versions/XXX_add_is_deadline_to_events.py
def upgrade():
    op.add_column('events', sa.Column('is_deadline', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('idx_events_is_deadline', 'events', ['is_deadline'], postgresql_where=text('is_deadline = true'))
```

### 2. Backend Model Changes

**EventSeries model:**
```python
# backend/src/models/event_series.py
deadline_date = Column(Date, nullable=True)
deadline_time = Column(Time, nullable=True)
```

**Event model:**
```python
# backend/src/models/event.py
is_deadline = Column(Boolean, default=False, nullable=False)
```

### 3. Backend Service Logic

**EventService deadline synchronization:**
```python
# backend/src/services/event_service.py

def _sync_deadline_entry(self, series: EventSeries) -> Event | None:
    """Create, update, or delete deadline entry based on series deadline."""
    existing = self.db.query(Event).filter(
        Event.series_id == series.id,
        Event.is_deadline == True,
        Event.deleted_at.is_(None)
    ).first()

    if series.deadline_date:
        if existing:
            # Update existing
            existing.title = f"[Deadline] {series.title}"
            existing.event_date = series.deadline_date
            existing.start_time = series.deadline_time
            existing.end_time = series.deadline_time
            existing.is_all_day = series.deadline_time is None
            return existing
        else:
            # Create new
            deadline = Event(
                title=f"[Deadline] {series.title}",
                event_date=series.deadline_date,
                start_time=series.deadline_time,
                end_time=series.deadline_time,
                is_all_day=series.deadline_time is None,
                input_timezone=series.input_timezone,
                series_id=series.id,
                organizer_id=series.organizer_id,
                is_deadline=True,
                status='future'
            )
            self.db.add(deadline)
            return deadline
    elif existing:
        # Remove deadline entry
        self.db.delete(existing)
    return None
```

### 4. API Protection

**Protect deadline entries from modification:**
```python
# backend/src/api/events.py

@router.patch("/events/{guid}")
def update_event(guid: str, update: EventUpdate):
    event = event_service.get_by_guid(guid)
    if event.is_deadline:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Deadline entries cannot be modified directly. Update the deadline on the parent Event Series instead.",
                "series_guid": event.series.guid if event.series else None
            }
        )
    # ... normal update logic
```

### 5. Frontend Changes

**Add is_deadline to Event type:**
```typescript
// frontend/src/contracts/api/event-api.ts
export interface Event {
  // ... existing fields
  is_deadline: boolean
}
```

**Update EventCard for deadline styling:**
```tsx
// frontend/src/components/events/EventCard.tsx
import { ClockAlert } from 'lucide-react'

const EventCard = ({ event }) => {
  const isDeadline = event.is_deadline

  return (
    <div className={cn(
      'border-l-4 p-2',
      isDeadline ? 'border-l-destructive' : getAttendanceBorder(event.attendance)
    )}>
      {isDeadline && (
        <ClockAlert className="h-4 w-4 text-destructive" />
      )}
      <span className={isDeadline ? 'text-destructive' : ''}>
        {event.title}
      </span>
    </div>
  )
}
```

## Testing

### Backend Tests

```python
# tests/unit/test_event_service_deadline.py

def test_create_series_with_deadline_creates_entry():
    """Creating series with deadline should create deadline entry."""
    series = event_service.create_series(
        title="Photo Shoot",
        deadline_date=date(2026, 3, 15),
        # ... other params
    )

    deadline = db.query(Event).filter(
        Event.series_id == series.id,
        Event.is_deadline == True
    ).first()

    assert deadline is not None
    assert deadline.title == "[Deadline] Photo Shoot"
    assert deadline.event_date == date(2026, 3, 15)

def test_update_event_rejects_deadline_entry():
    """Updating deadline entry should return 403."""
    # ... setup
    response = client.patch(f"/api/events/{deadline.guid}", json={"title": "New Title"})
    assert response.status_code == 403
```

### Frontend Tests

```typescript
// tests/components/events/EventCard.test.tsx

test('renders deadline with red styling', () => {
  const deadlineEvent = { ...mockEvent, is_deadline: true, title: '[Deadline] Test' }
  render(<EventCard event={deadlineEvent} />)

  expect(screen.getByText('[Deadline] Test')).toHaveClass('text-destructive')
  expect(screen.getByRole('img', { name: /clock/i })).toBeInTheDocument()
})
```

## API Examples

### Create Series with Deadline

```bash
POST /api/events/series
{
  "title": "Wedding Photography",
  "category_guid": "cat_01hgw2bbg...",
  "event_dates": ["2026-03-01", "2026-03-02"],
  "deadline_date": "2026-03-15",
  "deadline_time": "17:00:00"
}
```

### Update Series Deadline

```bash
PATCH /api/events/series/ser_01hgw2bbg...
{
  "deadline_date": "2026-03-20"
}
```

### Remove Series Deadline

```bash
PATCH /api/events/series/ser_01hgw2bbg...
{
  "deadline_date": null
}
```

### Attempt to Edit Deadline Entry (Rejected)

```bash
PATCH /api/events/evt_01hgw2bbg...  # deadline entry
{
  "title": "New Title"
}

# Response: 403 Forbidden
{
  "detail": "Deadline entries cannot be modified directly...",
  "series_guid": "ser_01hgw2bbg..."
}
```

## Validation Checklist

- [ ] Migrations created and tested
- [ ] EventSeries model has deadline_date and deadline_time
- [ ] Event model has is_deadline field
- [ ] EventService syncs deadline entry on series CRUD
- [ ] API rejects edit/delete on deadline entries
- [ ] Frontend shows deadline styling (red, icon)
- [ ] Frontend handles read-only view for deadlines
- [ ] Tests pass for all scenarios
