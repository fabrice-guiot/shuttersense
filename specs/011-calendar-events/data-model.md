# Data Model: Calendar of Events

**Feature Branch**: `011-calendar-events`
**Date**: 2026-01-11

## Entity Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Category     │     │    Location     │     │   Organizer     │
│   (cat_xxx)     │     │   (loc_xxx)     │     │   (org_xxx)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1:N                   │ 1:N                   │ 1:N
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Event                                  │
│                         (evt_xxx)                                │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Optional: series_id → EventSeries (ser_xxx)             │   │
│   │           sequence_number, total_in_series              │   │
│   └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ M:N via EventPerformer
                             ▼
                    ┌─────────────────┐
                    │   Performer     │
                    │   (prf_xxx)     │
                    └─────────────────┘
```

---

## Entity: Category

**GUID Prefix**: `cat_`
**Table**: `categories`
**Purpose**: Classification for events (Airshow, Wedding, Wildlife, etc.). Enforces grouping consistency between Events and their related entities.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID (never exposed) |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| `name` | String(100) | No | Unique | Category name |
| `color` | String(7) | Yes | - | Hex color code (e.g., "#FF5733") |
| `icon` | String(50) | Yes | - | Lucide icon name (e.g., "plane") |
| `is_active` | Boolean | No | Default: true | Soft enable/disable |
| `display_order` | Integer | No | Default: 0 | Sort order in UI |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **1:N** → Event (category_id)
- **1:N** → Location (category_id)
- **1:N** → Organizer (category_id)
- **1:N** → Performer (category_id)

### Validation Rules
- Name must be unique (case-insensitive)
- Color must be valid hex format if provided
- Cannot delete category with associated events (RESTRICT)

---

## Entity: Location

**GUID Prefix**: `loc_`
**Table**: `locations`
**Purpose**: Physical venues where events take place. Includes geocoded coordinates and default logistics settings.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| `name` | String(255) | No | - | Location display name |
| `address` | String(500) | Yes | - | Full street address |
| `city` | String(100) | Yes | - | City name |
| `state` | String(100) | Yes | - | State/province |
| `country` | String(100) | Yes | - | Country |
| `postal_code` | String(20) | Yes | - | ZIP/postal code |
| `latitude` | Decimal(10,7) | Yes | - | Geocoded latitude |
| `longitude` | Decimal(10,7) | Yes | - | Geocoded longitude |
| `timezone` | String(64) | Yes | - | IANA timezone (e.g., "America/New_York") |
| `category_id` | Integer | No | FK → categories | Must match event category |
| `rating` | Integer | Yes | 1-5 | Location rating (camera icons) |
| `timeoff_required_default` | Boolean | No | Default: false | Pre-select time-off for new events |
| `travel_required_default` | Boolean | No | Default: false | Pre-select travel for new events |
| `notes` | Text | Yes | - | Additional notes |
| `is_known` | Boolean | No | Default: false | Saved as "Known Location" |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **N:1** → Category (category_id)
- **1:N** → Event (location_id)
- **1:N** → EventSeries (location_id)

### Validation Rules
- If coordinates provided, both latitude and longitude required
- Rating must be 1-5 if provided
- Category must be active

---

## Entity: Organizer

**GUID Prefix**: `org_`
**Table**: `organizers`
**Purpose**: Event organizers/hosts. Tracks relationship and default ticket requirements.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| `name` | String(255) | No | - | Organizer name |
| `website` | String(500) | Yes | - | Website URL |
| `category_id` | Integer | No | FK → categories | Must match event category |
| `rating` | Integer | Yes | 1-5 | Organizer rating (stars) |
| `ticket_required_default` | Boolean | No | Default: false | Pre-select ticket for new events |
| `notes` | Text | Yes | - | Additional notes |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **N:1** → Category (category_id)
- **1:N** → Event (organizer_id)
- **1:N** → EventSeries (organizer_id)

### Validation Rules
- Website must be valid URL format if provided
- Rating must be 1-5 if provided
- Category must be active

---

## Entity: Performer

**GUID Prefix**: `prf_`
**Table**: `performers`
**Purpose**: Subjects/participants scheduled to appear at events (pilots, athletes, artists, etc.).

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| `name` | String(255) | No | - | Performer name |
| `category_id` | Integer | No | FK → categories | Must match event category |
| `website` | String(500) | Yes | - | Website URL |
| `instagram_handle` | String(100) | Yes | - | Instagram username (without @) |
| `additional_info` | Text | Yes | - | Multiline notes |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **N:1** → Category (category_id)
- **M:N** → Event (via EventPerformer)

### Validation Rules
- Website must be valid URL format if provided
- Instagram handle should not include @ symbol
- Category must be active

---

## Entity: EventSeries

**GUID Prefix**: `ser_`
**Table**: `event_series`
**Purpose**: Groups related events spanning multiple days. Stores shared properties that apply to all events in the series.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| `title` | String(255) | No | - | Series title (shared by all events) |
| `description` | Text | Yes | - | Series description |
| `category_id` | Integer | No | FK → categories | Category for all events in series |
| `location_id` | Integer | Yes | FK → locations | Default location |
| `organizer_id` | Integer | Yes | FK → organizers | Default organizer |
| `input_timezone` | String(64) | Yes | - | Timezone for time input display |
| `ticket_required` | Boolean | No | Default: false | Ticket requirement |
| `timeoff_required` | Boolean | No | Default: false | Time-off requirement |
| `travel_required` | Boolean | No | Default: false | Travel requirement |
| `total_events` | Integer | No | - | Number of events in series |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **N:1** → Category (category_id)
- **N:1** → Location (location_id)
- **N:1** → Organizer (organizer_id)
- **1:N** → Event (series_id, cascade delete)

### Validation Rules
- total_events must be >= 2 (otherwise not a series)
- Location category must match series category
- Organizer category must match series category

---

## Entity: Event

**GUID Prefix**: `evt_`
**Table**: `events`
**Purpose**: Individual calendar event. Can be standalone or part of a series.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `uuid` | UUID | No | Unique, Index | UUIDv7 for GUID generation |
| **Series Fields** |
| `series_id` | Integer | Yes | FK → event_series | NULL for standalone events |
| `sequence_number` | Integer | Yes | - | Position in series (1, 2, 3...) |
| **Core Fields** |
| `title` | String(255) | Yes | - | NULL = inherit from series |
| `description` | Text | Yes | - | NULL = inherit from series |
| `category_id` | Integer | Yes | FK → categories | NULL = inherit from series |
| `location_id` | Integer | Yes | FK → locations | NULL = inherit from series |
| `organizer_id` | Integer | Yes | FK → organizers | NULL = inherit from series |
| **Time Fields** |
| `event_date` | Date | No | Index | Event date |
| `start_time` | Time | Yes | - | NULL for all-day events |
| `end_time` | Time | Yes | - | NULL for all-day events |
| `is_all_day` | Boolean | No | Default: false | All-day event flag |
| `input_timezone` | String(64) | Yes | - | Timezone for input/display |
| **Status Fields** |
| `status` | String(50) | No | Default: "future" | Event status |
| `attendance` | String(50) | No | Default: "planned" | Attendance status |
| **Logistics Fields** |
| `ticket_required` | Boolean | Yes | - | NULL = inherit from series/organizer |
| `ticket_status` | String(50) | Yes | - | not_purchased, purchased, ready |
| `ticket_purchase_date` | Date | Yes | - | Required if purchased/ready |
| `timeoff_required` | Boolean | Yes | - | NULL = inherit from series/location |
| `timeoff_status` | String(50) | Yes | - | planned, booked, approved |
| `timeoff_booking_date` | Date | Yes | - | Required if booked/approved |
| `travel_required` | Boolean | Yes | - | NULL = inherit from series/location |
| `travel_status` | String(50) | Yes | - | planned, booked |
| `travel_booking_date` | Date | Yes | - | Required if booked |
| `deadline_date` | Date | Yes | - | Workflow completion deadline |
| **Soft Delete** |
| `deleted_at` | DateTime | Yes | Index | Soft delete timestamp |
| **Timestamps** |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |
| `updated_at` | DateTime | No | Default: utcnow | Last update timestamp |

### Relationships
- **N:1** → EventSeries (series_id, CASCADE on delete)
- **N:1** → Category (category_id)
- **N:1** → Location (location_id)
- **N:1** → Organizer (organizer_id)
- **M:N** → Performer (via EventPerformer)

### Computed Properties
- `effective_title`: Returns `title` or falls back to `series.title`
- `effective_category_id`: Returns `category_id` or falls back to `series.category_id`
- `series_indicator`: Returns "x/n" notation or null for standalone events

### Validation Rules
- Standalone events (no series_id): title and category_id required
- Series events: sequence_number required, title/category can be null
- If not is_all_day: start_time required
- If end_time provided: must be after start_time
- Location category must match event category (effective)
- Organizer category must match event category (effective)
- ticket_purchase_date required if ticket_status in (purchased, ready)
- timeoff_booking_date required if timeoff_status in (booked, approved)
- travel_booking_date required if travel_status == booked

### Status Enums

**Event Status** (configurable via Settings):
- `future` - Default
- `confirmed`
- `completed`
- `cancelled`

**Attendance Status**:
- `planned` - Yellow
- `attended` - Green
- `skipped` - Red

**Ticket Status**:
- `not_purchased` - Red
- `purchased` - Yellow
- `ready` - Green

**Time-off Status**:
- `planned` - Red
- `booked` - Yellow
- `approved` - Green

**Travel Status**:
- `planned` - Red
- `booked` - Green

---

## Entity: EventPerformer

**Table**: `event_performers`
**Purpose**: Junction table linking performers to events with attendance status.

### Fields

| Field | Type | Nullable | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | Integer | No | PK | Internal ID |
| `event_id` | Integer | No | FK → events | Event reference |
| `performer_id` | Integer | No | FK → performers | Performer reference |
| `status` | String(50) | No | Default: "confirmed" | Performer attendance status |
| `created_at` | DateTime | No | Default: utcnow | Creation timestamp |

### Relationships
- **N:1** → Event (event_id, CASCADE on delete)
- **N:1** → Performer (performer_id, RESTRICT on delete)

### Constraints
- Unique constraint on (event_id, performer_id)

### Status Enum

**Performer Status**:
- `confirmed` - Default
- `cancelled`

### Validation Rules
- Performer category must match event category (effective)

---

## Indexes

### Primary Indexes (Performance Critical)
```sql
-- Calendar queries
CREATE INDEX idx_events_date ON events(event_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_events_date_range ON events(event_date, deleted_at);

-- Series queries
CREATE INDEX idx_events_series ON events(series_id) WHERE series_id IS NOT NULL;

-- Category filtering
CREATE INDEX idx_events_category ON events(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_locations_category ON locations(category_id);
CREATE INDEX idx_organizers_category ON organizers(category_id);
CREATE INDEX idx_performers_category ON performers(category_id);
```

### Secondary Indexes
```sql
-- Known locations lookup
CREATE INDEX idx_locations_known ON locations(is_known, category_id) WHERE is_known = true;

-- Active categories
CREATE INDEX idx_categories_active ON categories(is_active, display_order) WHERE is_active = true;
```

---

## Cascade Behavior Summary

| Parent | Child | On Delete |
|--------|-------|-----------|
| Category | Event | RESTRICT |
| Category | Location | RESTRICT |
| Category | Organizer | RESTRICT |
| Category | Performer | RESTRICT |
| EventSeries | Event | CASCADE |
| Location | Event | SET NULL |
| Location | EventSeries | SET NULL |
| Organizer | Event | SET NULL |
| Organizer | EventSeries | SET NULL |
| Event | EventPerformer | CASCADE |
| Performer | EventPerformer | RESTRICT |

---

## Migration Sequence

1. `001_create_categories.py` - Categories table
2. `002_create_locations.py` - Locations table with category FK
3. `003_create_organizers.py` - Organizers table with category FK
4. `004_create_performers.py` - Performers table with category FK
5. `005_create_event_series.py` - EventSeries table
6. `006_create_events.py` - Events table with all FKs
7. `007_create_event_performers.py` - Junction table
8. `008_seed_default_categories.py` - Seed default categories (see table below)

---

## Default Category Seed Data

Migration `008_seed_default_categories.py` seeds the following categories:

| Name | Icon | Color | Rationale |
|------|------|-------|-----------|
| Airshow | `plane` | `#3B82F6` (blue) | Aviation theme |
| Wildlife | `bird` | `#22C55E` (green) | Nature theme |
| Wedding | `heart` | `#EC4899` (pink) | Romance theme |
| Sports | `trophy` | `#F97316` (orange) | Competition theme |
| Portrait | `user` | `#8B5CF6` (purple) | People theme |
| Concert | `music` | `#EF4444` (red) | Entertainment theme |
| Motorsports | `car` | `#6B7280` (gray) | Racing theme |

**Note**: All seeded categories have `is_active = true` and `display_order` set sequentially (0-6). Users may edit or delete seeded categories after initial setup.
