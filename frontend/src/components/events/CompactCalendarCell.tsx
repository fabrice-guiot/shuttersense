/**
 * CompactCalendarCell Component
 *
 * Mobile day cell with category badges for compact calendar view.
 * Feature: 016-mobile-calendar-view (GitHub Issue #69)
 *
 * Accessibility:
 * - ARIA labels for screen readers
 * - Keyboard navigation support
 * - Focus management
 */

import { useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { CategoryBadge } from './CategoryBadge'
import type { CategoryBadgeData } from './EventCalendar'

// ============================================================================
// Constants
// ============================================================================

/** Maximum category badges to show before overflow indicator */
const MAX_VISIBLE_BADGES = 4

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generates accessible label for compact day cell.
 */
function generateAriaLabel(
  date: Date,
  badges: CategoryBadgeData[],
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
    .slice(0, MAX_VISIBLE_BADGES)
    .map((b) => `${b.count} ${b.name}`)
    .join(', ')

  const overflow = overflowCount > 0 ? ` and ${overflowCount} more categories` : ''

  return `${dateStr}: ${totalEventCount} event${totalEventCount !== 1 ? 's' : ''} (${categoryList}${overflow})`
}

// ============================================================================
// CompactCalendarCell Component
// ============================================================================

export interface CompactCalendarCellProps {
  /** Date for this cell */
  date: Date
  /** Day number (1-31) */
  dayNumber: number
  /** Whether this day is in the current month */
  isCurrentMonth: boolean
  /** Whether this day is today */
  isToday: boolean
  /** Whether this cell has keyboard focus */
  isFocused: boolean
  /** Category badges to display */
  badges: CategoryBadgeData[]
  /** Number of additional categories not shown */
  overflowCount: number
  /** Total event count for this day */
  totalEventCount: number
  /** Click handler for day selection */
  onClick: (date: Date) => void
  /** Keyboard handler for accessibility */
  onKeyDown?: (e: React.KeyboardEvent) => void
  /** Focus handler */
  onFocus?: () => void
  /** Tab index for keyboard navigation */
  tabIndex?: number
  /** Additional CSS classes */
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
  onFocus,
  tabIndex = -1,
  className,
}: CompactCalendarCellProps) {
  const cellRef = useRef<HTMLDivElement>(null)
  const ariaLabel = generateAriaLabel(date, badges, totalEventCount, overflowCount)

  // Focus the cell when isFocused changes
  useEffect(() => {
    if (isFocused && cellRef.current) {
      cellRef.current.focus()
    }
  }, [isFocused])

  return (
    <div
      ref={cellRef}
      role="gridcell"
      tabIndex={tabIndex}
      aria-label={ariaLabel}
      aria-selected={isFocused}
      onFocus={onFocus}
      onKeyDown={onKeyDown}
      onClick={() => onClick(date)}
      className={cn(
        'min-h-[48px] p-1 border-b border-r border-border',
        'flex flex-col items-center gap-0.5',
        'cursor-pointer transition-colors',
        'hover:bg-accent/50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset',
        !isCurrentMonth && 'bg-muted/30 text-muted-foreground',
        className
      )}
    >
      {/* Day number */}
      <span
        className={cn(
          'text-sm font-medium',
          isToday &&
            'bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center'
        )}
      >
        {dayNumber}
      </span>

      {/* Category badges */}
      {badges.length > 0 && (
        <div className="flex flex-wrap gap-0.5 justify-center" role="list" aria-label="Event categories">
          {badges.slice(0, MAX_VISIBLE_BADGES).map((badge) => (
            <div key={badge.categoryGuid} role="listitem">
              <CategoryBadge
                icon={badge.icon}
                color={badge.color}
                count={badge.count}
                name={badge.name}
              />
            </div>
          ))}
          {overflowCount > 0 && (
            <span
              className="text-[10px] text-muted-foreground flex items-center"
              aria-label={`${overflowCount} more categories`}
            >
              +{overflowCount}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
