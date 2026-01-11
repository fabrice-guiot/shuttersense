# Quickstart: Calendar of Events

**Feature Branch**: `011-calendar-events`
**Date**: 2026-01-11

## Prerequisites

- Python 3.10+
- Node.js 20+
- PostgreSQL 12+ (or SQLite for development)
- Backend and frontend dependencies installed

## Quick Setup

```bash
# Checkout feature branch
git checkout 011-calendar-events

# Install new backend dependencies
cd backend
pip install geopy>=2.4.0 timezonefinder>=6.0.0

# Run database migrations (when implemented)
alembic upgrade head

# Start backend
uvicorn src.main:app --reload

# In another terminal, start frontend
cd frontend
npm run dev
```

## New GUID Prefixes

| Entity | Prefix | Example |
|--------|--------|---------|
| Event | `evt_` | `evt_01hgw2bbg0000000000000001` |
| EventSeries | `ser_` | `ser_01hgw2bbg0000000000000001` |
| Location | `loc_` | `loc_01hgw2bbg0000000000000001` |
| Organizer | `org_` | `org_01hgw2bbg0000000000000001` |
| Performer | `prf_` | `prf_01hgw2bbg0000000000000001` |
| Category | `cat_` | `cat_01hgw2bbg0000000000000001` |

## API Endpoints Overview

### Events
```
GET    /api/events                    # List events (with date/category filters)
GET    /api/events/stats              # TopHeader KPIs
POST   /api/events                    # Create event (or series if date range)
GET    /api/events/{guid}             # Get event details
PATCH  /api/events/{guid}             # Update event (?scope=series for bulk)
DELETE /api/events/{guid}             # Soft delete (?scope=series for bulk)
GET    /api/events/{guid}/performers  # List performers
POST   /api/events/{guid}/performers  # Add performer
DELETE /api/events/{guid}/performers/{guid}  # Remove performer
```

### Locations
```
GET    /api/locations                 # List known locations
POST   /api/locations                 # Create location
POST   /api/locations/geocode         # Geocode address
GET    /api/locations/{guid}          # Get location
PATCH  /api/locations/{guid}          # Update location
DELETE /api/locations/{guid}          # Delete location
```

### Organizers
```
GET    /api/organizers                # List organizers
POST   /api/organizers                # Create organizer
GET    /api/organizers/{guid}         # Get organizer
PATCH  /api/organizers/{guid}         # Update organizer
DELETE /api/organizers/{guid}         # Delete organizer
```

### Performers
```
GET    /api/performers                # List performers
POST   /api/performers                # Create performer
GET    /api/performers/{guid}         # Get performer
PATCH  /api/performers/{guid}         # Update performer
DELETE /api/performers/{guid}         # Delete performer
GET    /api/performers/{guid}/events  # List performer's events
```

### Categories
```
GET    /api/categories                # List categories
POST   /api/categories                # Create category
GET    /api/categories/{guid}         # Get category
PATCH  /api/categories/{guid}         # Update category
DELETE /api/categories/{guid}         # Delete category
POST   /api/categories/reorder        # Reorder categories
```

## Creating Events

### Single Event
```bash
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Oshkosh AirVenture 2026",
    "category_guid": "cat_01hgw2bbg...",
    "event_date": "2026-07-28",
    "start_time": "08:00:00",
    "end_time": "18:00:00",
    "input_timezone": "America/Chicago"
  }'
```

### Multi-Day Series
```bash
# Creates 3 events: Day 1, Day 2, Day 3 with "1/3", "2/3", "3/3" notation
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reno Air Races 2026",
    "category_guid": "cat_01hgw2bbg...",
    "event_date": "2026-09-18",
    "end_date": "2026-09-20",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "input_timezone": "America/Los_Angeles"
  }'
```

## Geocoding Addresses

```bash
curl -X POST http://localhost:8000/api/locations/geocode \
  -H "Content-Type: application/json" \
  -d '{"address": "Wittman Regional Airport, Oshkosh, WI"}'

# Response:
{
  "formatted_address": "Wittman Regional Airport, Oshkosh, WI 54902, USA",
  "latitude": 43.984167,
  "longitude": -88.556667,
  "timezone": "America/Chicago"
}
```

## Frontend Navigation

### Sidebar Structure
```
Dashboard
Collections
Pipelines
Events                    # NEW - Calendar view
Directory                 # NEW - Tabbed page
  ├── Locations (tab)
  ├── Organizers (tab)
  └── Performers (tab)
Analytics                 # Existing
Settings                  # NEW - Consolidates config
  ├── Categories (tab)    # NEW
  ├── Connectors (tab)    # MOVED from top-level
  └── Config (tab)        # MOVED from top-level
```

### Routes

| Page | Route | Description |
|------|-------|-------------|
| Events | `/events` | Calendar view with TopHeader KPIs |
| Directory | `/directory` | Tabbed page for Locations, Organizers, Performers |
| Directory/Locations | `/directory?tab=locations` | Manage known locations |
| Directory/Organizers | `/directory?tab=organizers` | Manage event organizers |
| Directory/Performers | `/directory?tab=performers` | Manage performers |
| Settings | `/settings` | Consolidated settings page |
| Settings/Categories | `/settings?tab=categories` | Manage event categories |
| Settings/Connectors | `/settings?tab=connectors` | Manage storage connectors |
| Settings/Config | `/settings?tab=config` | Application configuration |

**Note**: Old routes `/connectors` and `/config` redirect to their new Settings tabs.

## Key Components

### Backend
- `backend/src/models/event.py` - Event model with GuidMixin
- `backend/src/services/event_service.py` - Event CRUD and series logic
- `backend/src/services/geocoding_service.py` - Nominatim + timezonefinder
- `backend/src/api/events.py` - Event API router

### Frontend
- `frontend/src/pages/EventsPage.tsx` - Calendar page with TopHeader KPIs
- `frontend/src/pages/DirectoryPage.tsx` - Tabbed page (Locations | Organizers | Performers)
- `frontend/src/pages/SettingsPage.tsx` - Consolidated settings (Categories | Connectors | Config)
- `frontend/src/components/events/EventCalendar.tsx` - Month view calendar
- `frontend/src/components/directory/LocationsTab.tsx` - Locations management
- `frontend/src/components/settings/ConnectorsTab.tsx` - Refactored from ConnectorsPage
- `frontend/src/components/settings/ConfigTab.tsx` - Refactored from ConfigPage
- `frontend/src/hooks/useEvents.ts` - Events CRUD hook
- `frontend/src/hooks/useEventStats.ts` - TopHeader KPIs

## Attendance Status Colors

| Status | Color | Badge Variant |
|--------|-------|---------------|
| Planned | Yellow | `warning` |
| Attended | Green | `success` |
| Skipped | Red | `destructive` |

## Logistics Status Colors

| Requirement | Red | Yellow | Green |
|-------------|-----|--------|-------|
| Ticket | Not Purchased | Purchased | Ready |
| Time-off | Planned | Booked | Approved |
| Travel | Planned | - | Booked |

## Testing

```bash
# Backend tests
cd backend
python -m pytest tests/unit/test_event_service.py -v
python -m pytest tests/unit/test_geocoding_service.py -v

# Frontend tests
cd frontend
npm run test -- EventCalendar
```

## Default Categories (Seeded)

- Airshow (icon: `plane`)
- Wildlife (icon: `camera`)
- Sports (icon: `trophy`)
- Wedding (icon: `heart`)
- Portrait (icon: `user`)
- Concert (icon: `music`)
- Motorsports (icon: `car`)
