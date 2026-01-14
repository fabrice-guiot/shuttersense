# Data Model: Mobile Calendar View

**Feature Branch**: `016-mobile-calendar-view`
**Date**: 2026-01-13

## Overview

This feature introduces no new database entities or backend changes. It adds frontend-only components for responsive calendar display. This document defines the component data structures and their relationships.

---

## Component Data Structures

### 1. CategoryBadgeData

Represents a category with its event count for a specific day.

```typescript
interface CategoryBadgeData {
  /** Category GUID (e.g., "cat_01hgw2bbg...") */
  categoryGuid: string

  /** Category display name */
  name: string

  /** Lucide icon name from ICON_MAP */
  icon: string | null

  /** Category color (hex format, e.g., "#3b82f6") */
  color: string | null

  /** Number of events in this category for the day */
  count: number
}
```

**Source**: Derived from `Event.category` in existing event data.

---

### 2. CompactDayData

Represents a day's data in compact calendar mode.

```typescript
interface CompactDayData {
  /** Date object for this day */
  date: Date

  /** ISO date string (YYYY-MM-DD) */
  dateString: string

  /** Day number (1-31) */
  dayNumber: number

  /** Whether this day is in the current month */
  isCurrentMonth: boolean

  /** Whether this day is today */
  isToday: boolean

  /** Whether this day has keyboard focus */
  isFocused: boolean

  /** Whether this day is selected */
  isSelected: boolean

  /** Category badges to display (max 4 + overflow) */
  badges: CategoryBadgeData[]

  /** Total event count for accessibility label */
  totalEventCount: number

  /** Overflow count when >4 categories exist */
  overflowCount: number
}
```

**Derivation Rules**:
- `badges`: First 4 categories sorted by count (descending)
- `overflowCount`: Total categories minus 4 (when > 4)
- `totalEventCount`: Sum of all event counts across all categories

---

### 3. CalendarViewMode

Enum for calendar display modes.

```typescript
type CalendarViewMode = 'compact' | 'standard'
```

**Mode Selection**:
- `compact`: Viewport width < 640px
- `standard`: Viewport width >= 640px

---

## Data Transformations

### Event to CategoryBadge Transformation

```typescript
/**
 * Groups events by category and returns badge data.
 *
 * @param events - Events for a single day
 * @returns Array of CategoryBadgeData sorted by count (descending)
 */
function groupEventsByCategory(events: Event[]): CategoryBadgeData[]

// Example transformation:
// Input: [
//   { title: "Concert A", category: { guid: "cat_1", name: "Music", icon: "music", color: "#3b82f6" } },
//   { title: "Concert B", category: { guid: "cat_1", name: "Music", icon: "music", color: "#3b82f6" } },
//   { title: "Game", category: { guid: "cat_2", name: "Sports", icon: "trophy", color: "#10b981" } }
// ]
// Output: [
//   { categoryGuid: "cat_1", name: "Music", icon: "music", color: "#3b82f6", count: 2 },
//   { categoryGuid: "cat_2", name: "Sports", icon: "trophy", color: "#10b981", count: 1 }
// ]
```

---

### Day Events to CompactDayData Transformation

```typescript
/**
 * Transforms day and events into compact display data.
 *
 * @param date - Date for this day
 * @param events - Events for this day
 * @param currentMonth - Current month being displayed
 * @param today - Today's date
 * @param focusedDate - Currently focused date (keyboard nav)
 * @param selectedDate - Currently selected date
 * @returns CompactDayData for rendering
 */
function createCompactDayData(
  date: Date,
  events: Event[],
  currentMonth: Date,
  today: Date,
  focusedDate: Date | null,
  selectedDate: Date | null
): CompactDayData
```

---

## Existing Data Dependencies

This feature uses existing data structures without modification:

### Event (from `frontend/src/contracts/api/event-api.ts`)

```typescript
interface Event {
  guid: string
  title: string
  event_date: string  // YYYY-MM-DD
  category: {
    guid: string
    name: string
    icon: string | null
    color: string | null
  } | null
  // ... other fields not needed for compact view
}
```

### Category (from `frontend/src/contracts/api/category-api.ts`)

```typescript
interface Category {
  guid: string
  name: string
  icon: string | null
  color: string | null
  is_active: boolean
}
```

---

## State Management

No new global state required. All state is managed locally:

| State | Location | Purpose |
|-------|----------|---------|
| View mode | CSS media query | Responsive layout switching |
| Focused cell | EventCalendar (existing) | Keyboard navigation |
| Selected day | EventCalendar (existing) | Day detail dialog |
| Events by date | useCalendar (existing) | Event data |

---

## Accessibility Data

### ARIA Label Generation

```typescript
/**
 * Generates accessible label for compact day cell.
 *
 * @param data - CompactDayData for the cell
 * @returns Accessible label string
 */
function generateCompactDayAriaLabel(data: CompactDayData): string

// Example outputs:
// - "January 15, 2026: 3 events in 2 categories (2 Music, 1 Sports)"
// - "January 16, 2026: No events"
// - "January 17, 2026: 5 events in 4 categories and 2 more"
```

---

## Data Flow Diagram

```text
┌─────────────────┐
│ useCalendar()   │ ← Existing hook, provides events by date
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ EventCalendar Component                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ For each day in calendar grid:                           │ │
│ │                                                          │ │
│ │ ┌───────────┐    ┌─────────────────────┐                │ │
│ │ │ Desktop   │    │ Mobile (<640px)      │                │ │
│ │ │ (>=640px) │    │                      │                │ │
│ │ │           │    │ groupEventsByCategory│                │ │
│ │ │ EventCard │    │         │            │                │ │
│ │ │ (compact) │    │         ▼            │                │ │
│ │ │           │    │ CategoryBadgeData[]  │                │ │
│ │ │           │    │         │            │                │ │
│ │ │           │    │         ▼            │                │ │
│ │ │           │    │ CompactCalendarCell  │                │ │
│ │ │           │    │    └── CategoryBadge │                │ │
│ │ └───────────┘    └─────────────────────┘                │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │
         │ onDayClick (existing)
         ▼
┌─────────────────┐
│ Day Detail      │ ← Existing dialog, unchanged
│ Dialog          │
└─────────────────┘
```

---

## Validation Rules

### CategoryBadgeData Validation

| Field | Rule |
|-------|------|
| count | Must be >= 1 (categories with 0 events are filtered out) |
| count display | Show "99+" if count > 99 |
| icon | Falls back to default icon if null |
| color | Falls back to default color if null |

### CompactDayData Validation

| Field | Rule |
|-------|------|
| badges | Maximum 4 items; overflow goes to overflowCount |
| badges order | Sorted by count descending (most events first) |
| overflowCount | 0 if <= 4 categories; otherwise (total - 4) |

---

## Constants

```typescript
/** Maximum category badges to show before overflow indicator */
const MAX_VISIBLE_BADGES = 4

/** Maximum count to display before showing "99+" */
const MAX_DISPLAY_COUNT = 99

/** Compact cell minimum height in pixels */
const COMPACT_CELL_HEIGHT = 48

/** Standard cell minimum height in pixels */
const STANDARD_CELL_HEIGHT = 100

/** Mobile breakpoint in pixels (Tailwind sm:) */
const MOBILE_BREAKPOINT = 640
```
