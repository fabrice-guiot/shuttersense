# Quickstart: Mobile Calendar View

**Feature Branch**: `016-mobile-calendar-view`
**Date**: 2026-01-13

## Overview

This guide provides implementation instructions for the Mobile Calendar View feature. The feature adds a compact calendar display for mobile devices (< 640px viewport) using category badges instead of full event cards.

---

## Prerequisites

- Node.js 18+ and pnpm installed
- Frontend development server running (`pnpm dev` in `frontend/`)
- Familiarity with React, TypeScript, and Tailwind CSS
- Chrome DevTools (or similar) for responsive testing

---

## Implementation Order

Follow this order to maintain testability at each step:

### Step 1: Create `useMediaQuery` Hook

**File**: `frontend/src/hooks/useMediaQuery.ts`

A reusable hook for responsive behavior:

```typescript
import { useState, useEffect } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    // SSR safety: default to false
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mediaQuery = window.matchMedia(query)
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches)

    // Set initial value
    setMatches(mediaQuery.matches)

    // Listen for changes
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [query])

  return matches
}

// Convenience hook for mobile detection
export function useIsMobile(): boolean {
  return !useMediaQuery('(min-width: 640px)')
}
```

**Test**: `frontend/tests/hooks/useMediaQuery.test.ts`

---

### Step 2: Create `CategoryBadge` Component

**File**: `frontend/src/components/events/CategoryBadge.tsx`

Displays a category icon with count:

```typescript
import { ICON_MAP } from '@/utils/icon-map'  // Existing icon mapping
import { cn } from '@/lib/utils'

interface CategoryBadgeProps {
  icon: string | null
  color: string | null
  count: number
  name: string
  className?: string
}

export function CategoryBadge({ icon, color, count, name, className }: CategoryBadgeProps) {
  const Icon = icon ? ICON_MAP[icon] : null
  const displayCount = count > 99 ? '99+' : count.toString()

  return (
    <div
      className={cn(
        'relative inline-flex items-center justify-center',
        'h-5 w-5 rounded-sm',
        className
      )}
      style={{ backgroundColor: color ? `${color}20` : undefined }}
      title={`${count} ${name} event${count !== 1 ? 's' : ''}`}
    >
      {Icon && (
        <Icon
          className="h-3 w-3"
          style={{ color: color || undefined }}
          aria-hidden="true"
        />
      )}
      {count > 1 && (
        <span
          className={cn(
            'absolute -bottom-1 -right-1',
            'min-w-[14px] h-[14px] px-0.5',
            'flex items-center justify-center',
            'text-[10px] font-medium leading-none',
            'bg-background border border-border rounded-full'
          )}
        >
          {displayCount}
        </span>
      )}
    </div>
  )
}
```

**Test**: `frontend/tests/components/events/CategoryBadge.test.tsx`

---

### Step 3: Create `CompactCalendarCell` Component

**File**: `frontend/src/components/events/CompactCalendarCell.tsx`

Mobile day cell with badges:

```typescript
import { cn } from '@/lib/utils'
import { CategoryBadge } from './CategoryBadge'

interface CompactCalendarCellProps {
  date: Date
  dayNumber: number
  isCurrentMonth: boolean
  isToday: boolean
  isFocused: boolean
  badges: Array<{
    categoryGuid: string
    icon: string | null
    color: string | null
    count: number
    name: string
  }>
  overflowCount: number
  totalEventCount: number
  onClick: (date: Date) => void
  onKeyDown?: (event: React.KeyboardEvent, date: Date) => void
  className?: string
}

export function CompactCalendarCell({
  date,
  dayNumber,
  isCurrentMonth,
  isToday,
  isFocused,
  badges,
  overflowCount,
  totalEventCount,
  onClick,
  onKeyDown,
  className,
}: CompactCalendarCellProps) {
  const ariaLabel = generateAriaLabel(date, badges, totalEventCount, overflowCount)

  return (
    <div
      role="gridcell"
      tabIndex={isFocused ? 0 : -1}
      aria-label={ariaLabel}
      aria-selected={isFocused}
      className={cn(
        'min-h-[48px] p-1 border-b border-r border-border',
        'flex flex-col items-center gap-0.5',
        'cursor-pointer transition-colors',
        'hover:bg-accent/50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset',
        !isCurrentMonth && 'bg-muted/30 text-muted-foreground',
        className
      )}
      onClick={() => onClick(date)}
      onKeyDown={(e) => onKeyDown?.(e, date)}
    >
      {/* Day number */}
      <span
        className={cn(
          'text-sm font-medium',
          isToday && 'bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center'
        )}
      >
        {dayNumber}
      </span>

      {/* Category badges */}
      {badges.length > 0 && (
        <div className="flex flex-wrap gap-0.5 justify-center">
          {badges.slice(0, 4).map((badge) => (
            <CategoryBadge
              key={badge.categoryGuid}
              icon={badge.icon}
              color={badge.color}
              count={badge.count}
              name={badge.name}
            />
          ))}
          {overflowCount > 0 && (
            <span className="text-[10px] text-muted-foreground">
              +{overflowCount}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function generateAriaLabel(
  date: Date,
  badges: Array<{ name: string; count: number }>,
  totalEventCount: number,
  overflowCount: number
): string {
  const dateStr = date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  if (totalEventCount === 0) {
    return `${dateStr}: No events`
  }

  const categoryList = badges
    .slice(0, 4)
    .map((b) => `${b.count} ${b.name}`)
    .join(', ')

  const overflow = overflowCount > 0 ? ` and ${overflowCount} more categories` : ''

  return `${dateStr}: ${totalEventCount} events (${categoryList}${overflow})`
}
```

**Test**: `frontend/tests/components/events/CompactCalendarCell.test.tsx`

---

### Step 4: Modify `EventCalendar.tsx`

**File**: `frontend/src/components/events/EventCalendar.tsx`

Add responsive layout switching:

```typescript
// Add import
import { useIsMobile } from '@/hooks/useMediaQuery'
import { CompactCalendarCell } from './CompactCalendarCell'

// Inside EventCalendar component
export function EventCalendar({ /* existing props */ }) {
  const isMobile = useIsMobile()

  // ... existing code ...

  // In the day cell rendering section, add conditional:
  return (
    <div className="...">
      {/* Header row - unchanged */}

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {calendarDays.map((day) => {
          const dayEvents = eventsByDate.get(day.dateString) || []

          if (isMobile) {
            const badges = groupEventsByCategory(dayEvents)
            return (
              <CompactCalendarCell
                key={day.dateString}
                date={day.date}
                dayNumber={day.dayNumber}
                isCurrentMonth={day.isCurrentMonth}
                isToday={day.isToday}
                isFocused={focusedIndex === day.index}
                badges={badges.slice(0, 4)}
                overflowCount={Math.max(0, badges.length - 4)}
                totalEventCount={dayEvents.length}
                onClick={handleDayClick}
                onKeyDown={handleKeyDown}
              />
            )
          }

          // Existing standard cell rendering
          return (
            <div key={day.dateString} /* existing desktop cell */ >
              {/* ... existing EventCard rendering ... */}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Add helper function
function groupEventsByCategory(events: Event[]): CategoryBadgeData[] {
  const grouped = new Map<string, CategoryBadgeData>()

  events.forEach((event) => {
    const key = event.category?.guid || 'uncategorized'
    const existing = grouped.get(key)

    if (existing) {
      existing.count++
    } else {
      grouped.set(key, {
        categoryGuid: key,
        name: event.category?.name || 'Uncategorized',
        icon: event.category?.icon || null,
        color: event.category?.color || null,
        count: 1,
      })
    }
  })

  // Sort by count descending
  return Array.from(grouped.values()).sort((a, b) => b.count - a.count)
}
```

---

### Step 5: Adjust Cell Heights with Responsive Classes

In `EventCalendar.tsx`, update the cell classes:

```typescript
// Change from:
className="min-h-[100px] p-1 border-b border-r border-border"

// To:
className="min-h-[48px] sm:min-h-[100px] p-1 border-b border-r border-border"
```

This applies:
- Mobile (< 640px): `min-h-[48px]`
- Tablet+ (>= 640px): `min-h-[100px]`

---

## Testing Guide

### Manual Testing

1. **Open DevTools** → Toggle device toolbar (Ctrl+Shift+M / Cmd+Shift+M)
2. **Test breakpoint** at 640px:
   - 639px: Should show compact badges
   - 640px: Should show standard event cards
3. **Test interactions**:
   - Tap day with events → Day Detail popup opens
   - Tap event in popup → Event View opens
   - Tap Edit → Event Form opens
4. **Test edge cases**:
   - Day with 5+ categories → Shows 4 badges + "+N" overflow
   - Category with 100+ events → Shows "99+"
   - Empty day → Shows only day number

### Automated Tests

Run tests:

```bash
cd frontend
pnpm test                           # All tests
pnpm test useMediaQuery             # Hook tests
pnpm test CategoryBadge             # Badge tests
pnpm test CompactCalendarCell       # Cell tests
pnpm test EventCalendar             # Integration tests
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/hooks/useMediaQuery.ts` | Viewport detection hook |
| `src/components/events/CategoryBadge.tsx` | Icon + count badge |
| `src/components/events/CompactCalendarCell.tsx` | Mobile day cell |
| `src/components/events/EventCalendar.tsx` | Main calendar (modified) |
| `tests/hooks/useMediaQuery.test.ts` | Hook tests |
| `tests/components/events/CategoryBadge.test.tsx` | Badge tests |
| `tests/components/events/CompactCalendarCell.test.tsx` | Cell tests |

---

## Common Pitfalls

1. **SSR Hydration Mismatch**: Use `useEffect` for `matchMedia` initial state, not inline
2. **Touch Target Size**: Ensure cells are at least 44px (48px used here)
3. **Icon Import**: Use existing `ICON_MAP` from `@/utils/icon-map`
4. **Color Opacity**: Use `${color}20` format for 12% opacity backgrounds
5. **Test Setup**: Remember to mock `window.matchMedia` in tests

---

## Verification Checklist

Before marking complete:

- [ ] Compact view appears on viewports < 640px
- [ ] Standard view appears on viewports >= 640px
- [ ] Day tap opens Day Detail popup
- [ ] All existing dialog flows work on mobile
- [ ] Keyboard navigation works in compact mode
- [ ] Screen readers announce category counts
- [ ] No horizontal scroll on mobile
- [ ] Tests pass: `pnpm test`
- [ ] TypeScript compiles: `pnpm build`
