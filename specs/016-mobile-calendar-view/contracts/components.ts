/**
 * Component Contracts: Mobile Calendar View
 *
 * Feature Branch: 016-mobile-calendar-view
 * Date: 2026-01-13
 *
 * This file defines TypeScript interfaces for new components.
 * These contracts serve as the implementation specification.
 */

import type { LucideIcon } from 'lucide-react'

// =============================================================================
// Data Types
// =============================================================================

/**
 * Category badge display data for a single category on a day.
 */
export interface CategoryBadgeData {
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

/**
 * Compact day cell display data.
 */
export interface CompactDayData {
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

  /** Category badges to display (max 4) */
  badges: CategoryBadgeData[]

  /** Total event count for accessibility label */
  totalEventCount: number

  /** Overflow count when >4 categories exist */
  overflowCount: number
}

/**
 * Calendar view mode for responsive display.
 */
export type CalendarViewMode = 'compact' | 'standard'

// =============================================================================
// Component Props
// =============================================================================

/**
 * Props for CategoryBadge component.
 *
 * Displays a category icon with event count badge.
 */
export interface CategoryBadgeProps {
  /** Category data including icon, color, and count */
  data: CategoryBadgeData

  /** Additional CSS classes */
  className?: string
}

/**
 * Props for CompactCalendarCell component.
 *
 * Renders a day cell in compact (mobile) mode with category badges.
 */
export interface CompactCalendarCellProps {
  /** Day data including badges and state */
  data: CompactDayData

  /** Click handler for day selection */
  onClick: (date: Date) => void

  /** Keyboard handler for accessibility */
  onKeyDown?: (event: React.KeyboardEvent, date: Date) => void

  /** Additional CSS classes */
  className?: string
}

/**
 * Props for overflow badge ("+N more" indicator).
 */
export interface OverflowBadgeProps {
  /** Number of additional categories not shown */
  count: number

  /** Additional CSS classes */
  className?: string
}

// =============================================================================
// Hook Returns
// =============================================================================

/**
 * Return type for useMediaQuery hook.
 */
export interface UseMediaQueryReturn {
  /** Whether the media query matches */
  matches: boolean
}

/**
 * Return type for useCalendarViewMode hook.
 */
export interface UseCalendarViewModeReturn {
  /** Current view mode based on viewport */
  viewMode: CalendarViewMode

  /** Whether in mobile/compact mode */
  isMobile: boolean
}

// =============================================================================
// Utility Function Signatures
// =============================================================================

/**
 * Groups events by category and returns badge data.
 *
 * @param events - Events for a single day
 * @returns Array of CategoryBadgeData sorted by count (descending)
 */
export type GroupEventsByCategory = (events: Event[]) => CategoryBadgeData[]

/**
 * Creates compact day data from day and events.
 *
 * @param date - Date for this day
 * @param events - Events for this day
 * @param options - Additional state (currentMonth, today, focused, selected)
 * @returns CompactDayData for rendering
 */
export type CreateCompactDayData = (
  date: Date,
  events: Event[],
  options: {
    currentMonth: Date
    today: Date
    focusedDate: Date | null
    selectedDate: Date | null
  }
) => CompactDayData

/**
 * Generates accessible label for compact day cell.
 *
 * @param data - CompactDayData for the cell
 * @returns Accessible label string
 */
export type GenerateCompactDayAriaLabel = (data: CompactDayData) => string

// =============================================================================
// Constants
// =============================================================================

/** Maximum category badges to show before overflow indicator */
export const MAX_VISIBLE_BADGES = 4

/** Maximum count to display before showing "99+" */
export const MAX_DISPLAY_COUNT = 99

/** Compact cell minimum height in pixels */
export const COMPACT_CELL_HEIGHT = 48

/** Standard cell minimum height in pixels */
export const STANDARD_CELL_HEIGHT = 100

/** Mobile breakpoint in pixels (Tailwind sm:) */
export const MOBILE_BREAKPOINT = 640

// =============================================================================
// Event Type Reference (from existing contracts)
// =============================================================================

/**
 * Minimal Event interface needed for compact view.
 * Full interface is in frontend/src/contracts/api/event-api.ts
 */
export interface EventForCompactView {
  guid: string
  title: string
  event_date: string
  category: {
    guid: string
    name: string
    icon: string | null
    color: string | null
  } | null
}
