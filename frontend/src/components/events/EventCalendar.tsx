/**
 * EventCalendar Component
 *
 * Month grid calendar view for displaying events
 * Issue #39 - Calendar Events feature (Phase 4)
 *
 * Accessibility (Phase 13):
 * - Keyboard navigation: Arrow keys to navigate dates
 * - ARIA labels for screen readers
 * - Focus management for calendar cells
 */

import { useMemo, useState, useCallback, useRef, useEffect } from 'react'
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { EventCard } from './EventCard'
import type { Event } from '@/contracts/api/event-api'

// ============================================================================
// Calendar Utilities
// ============================================================================

const WEEKDAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

interface CalendarDay {
  date: Date
  dateString: string // YYYY-MM-DD
  isCurrentMonth: boolean
  isToday: boolean
  events: Event[]
}

/**
 * Generate calendar grid for a given month
 */
function generateCalendarDays(
  year: number,
  month: number,
  events: Event[]
): CalendarDay[] {
  const days: CalendarDay[] = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // First day of the month
  const firstOfMonth = new Date(year, month - 1, 1)
  const startDayOfWeek = firstOfMonth.getDay()

  // Last day of the month
  const lastOfMonth = new Date(year, month, 0)
  const daysInMonth = lastOfMonth.getDate()

  // Build event lookup by date string
  const eventsByDate = new Map<string, Event[]>()
  events.forEach(event => {
    const dateStr = event.event_date
    if (!eventsByDate.has(dateStr)) {
      eventsByDate.set(dateStr, [])
    }
    eventsByDate.get(dateStr)!.push(event)
  })

  // Helper to format date as YYYY-MM-DD
  const formatDateString = (d: Date): string => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  // Add days from previous month to fill first week
  const prevMonth = new Date(year, month - 2, 1)
  const daysInPrevMonth = new Date(year, month - 1, 0).getDate()
  for (let i = startDayOfWeek - 1; i >= 0; i--) {
    const date = new Date(prevMonth.getFullYear(), prevMonth.getMonth(), daysInPrevMonth - i)
    const dateString = formatDateString(date)
    days.push({
      date,
      dateString,
      isCurrentMonth: false,
      isToday: date.getTime() === today.getTime(),
      events: eventsByDate.get(dateString) || []
    })
  }

  // Add days of current month
  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month - 1, day)
    const dateString = formatDateString(date)
    days.push({
      date,
      dateString,
      isCurrentMonth: true,
      isToday: date.getTime() === today.getTime(),
      events: eventsByDate.get(dateString) || []
    })
  }

  // Add days from next month to complete grid (6 rows = 42 days)
  const remainingDays = 42 - days.length
  for (let day = 1; day <= remainingDays; day++) {
    const date = new Date(year, month, day)
    const dateString = formatDateString(date)
    days.push({
      date,
      dateString,
      isCurrentMonth: false,
      isToday: date.getTime() === today.getTime(),
      events: eventsByDate.get(dateString) || []
    })
  }

  return days
}

// ============================================================================
// CalendarHeader Component
// ============================================================================

interface CalendarHeaderProps {
  year: number
  month: number
  onPreviousMonth: () => void
  onNextMonth: () => void
  onToday: () => void
}

const CalendarHeader = ({
  year,
  month,
  onPreviousMonth,
  onNextMonth,
  onToday
}: CalendarHeaderProps) => {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-xl font-semibold">
        {MONTH_NAMES[month - 1]} {year}
      </h2>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onToday}
          className="hidden sm:inline-flex"
        >
          <CalendarIcon className="h-4 w-4 mr-1" />
          Today
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={onPreviousMonth}
          aria-label="Previous month"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={onNextMonth}
          aria-label="Next month"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

// ============================================================================
// CalendarCell Component
// ============================================================================

interface CalendarCellProps {
  day: CalendarDay
  onEventClick?: (event: Event) => void
  onDayClick?: (date: Date) => void
  maxEventsToShow?: number
  isFocused?: boolean
  onFocus?: () => void
  tabIndex?: number
  onKeyDown?: (e: React.KeyboardEvent) => void
}

const CalendarCell = ({
  day,
  onEventClick,
  onDayClick,
  maxEventsToShow = 3,
  isFocused = false,
  onFocus,
  tabIndex = -1,
  onKeyDown
}: CalendarCellProps) => {
  const cellRef = useRef<HTMLDivElement>(null)
  const visibleEvents = day.events.slice(0, maxEventsToShow)
  const hiddenCount = day.events.length - maxEventsToShow

  // When there's only one event, allow it to expand and wrap text
  const isSingleEvent = day.events.length === 1

  // Focus the cell when isFocused changes
  useEffect(() => {
    if (isFocused && cellRef.current) {
      cellRef.current.focus()
    }
  }, [isFocused])

  // Format date for ARIA label
  const ariaLabel = `${day.date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  })}${day.events.length > 0 ? `, ${day.events.length} event${day.events.length !== 1 ? 's' : ''}` : ', no events'}${day.isToday ? ', today' : ''}`

  return (
    <div
      ref={cellRef}
      role="gridcell"
      aria-label={ariaLabel}
      aria-selected={isFocused}
      tabIndex={tabIndex}
      onFocus={onFocus}
      onKeyDown={onKeyDown}
      className={cn(
        'min-h-[100px] p-1 border-b border-r border-border',
        'flex flex-col',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset',
        !day.isCurrentMonth && 'bg-muted/30'
      )}
    >
      {/* Day Number */}
      <button
        onClick={() => onDayClick?.(day.date)}
        tabIndex={-1}
        aria-hidden="true"
        className={cn(
          'w-7 h-7 flex items-center justify-center rounded-full text-sm mb-1',
          'hover:bg-accent transition-colors',
          day.isToday && 'bg-primary text-primary-foreground font-semibold',
          !day.isCurrentMonth && 'text-muted-foreground'
        )}
      >
        {day.date.getDate()}
      </button>

      {/* Events */}
      <div className="flex-1 space-y-0.5 overflow-hidden" role="list" aria-label="Events on this day">
        {visibleEvents.map(event => (
          <EventCard
            key={event.guid}
            event={event}
            onClick={onEventClick}
            compact
            expanded={isSingleEvent}
          />
        ))}

        {/* More events indicator */}
        {hiddenCount > 0 && (
          <button
            onClick={() => onDayClick?.(day.date)}
            tabIndex={-1}
            className="w-full text-left px-1.5 py-0.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded transition-colors"
            aria-label={`${hiddenCount} more events, click to view all`}
          >
            +{hiddenCount} more
          </button>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// EventCalendar Component
// ============================================================================

interface EventCalendarProps {
  events: Event[]
  year: number
  month: number
  loading?: boolean
  onPreviousMonth: () => void
  onNextMonth: () => void
  onToday: () => void
  onEventClick?: (event: Event) => void
  onDayClick?: (date: Date) => void
  className?: string
}

export const EventCalendar = ({
  events,
  year,
  month,
  loading = false,
  onPreviousMonth,
  onNextMonth,
  onToday,
  onEventClick,
  onDayClick,
  className
}: EventCalendarProps) => {
  // Generate calendar days with events
  const calendarDays = useMemo(
    () => generateCalendarDays(year, month, events),
    [year, month, events]
  )

  // Track focused cell index for keyboard navigation
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null)

  // Find the index of today or first day of current month for initial focus
  const getInitialFocusIndex = useCallback(() => {
    const todayIndex = calendarDays.findIndex(d => d.isToday && d.isCurrentMonth)
    if (todayIndex >= 0) return todayIndex
    return calendarDays.findIndex(d => d.isCurrentMonth)
  }, [calendarDays])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent, currentIndex: number) => {
    let newIndex: number | null = null
    const totalDays = calendarDays.length
    const cols = 7

    switch (e.key) {
      case 'ArrowLeft':
        e.preventDefault()
        newIndex = currentIndex > 0 ? currentIndex - 1 : currentIndex
        break
      case 'ArrowRight':
        e.preventDefault()
        newIndex = currentIndex < totalDays - 1 ? currentIndex + 1 : currentIndex
        break
      case 'ArrowUp':
        e.preventDefault()
        newIndex = currentIndex >= cols ? currentIndex - cols : currentIndex
        break
      case 'ArrowDown':
        e.preventDefault()
        newIndex = currentIndex + cols < totalDays ? currentIndex + cols : currentIndex
        break
      case 'Home':
        e.preventDefault()
        // Go to start of current row
        newIndex = Math.floor(currentIndex / cols) * cols
        break
      case 'End':
        e.preventDefault()
        // Go to end of current row
        newIndex = Math.floor(currentIndex / cols) * cols + cols - 1
        break
      case 'PageUp':
        e.preventDefault()
        onPreviousMonth()
        return
      case 'PageDown':
        e.preventDefault()
        onNextMonth()
        return
      case 'Enter':
      case ' ':
        e.preventDefault()
        onDayClick?.(calendarDays[currentIndex].date)
        return
      default:
        return
    }

    if (newIndex !== null && newIndex !== currentIndex) {
      setFocusedIndex(newIndex)
    }
  }, [calendarDays, onDayClick, onPreviousMonth, onNextMonth])

  // Reset focus when month changes
  useEffect(() => {
    setFocusedIndex(null)
  }, [year, month])

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header with navigation */}
      <CalendarHeader
        year={year}
        month={month}
        onPreviousMonth={onPreviousMonth}
        onNextMonth={onNextMonth}
        onToday={onToday}
      />

      {/* Calendar Grid */}
      <div
        role="grid"
        aria-label={`Calendar for ${MONTH_NAMES[month - 1]} ${year}`}
        className="border-t border-l border-border rounded-lg overflow-hidden bg-card"
      >
        {/* Weekday headers */}
        <div role="row" className="grid grid-cols-7">
          {WEEKDAY_NAMES.map(day => (
            <div
              key={day}
              role="columnheader"
              aria-label={day === 'Sun' ? 'Sunday' : day === 'Mon' ? 'Monday' : day === 'Tue' ? 'Tuesday' : day === 'Wed' ? 'Wednesday' : day === 'Thu' ? 'Thursday' : day === 'Fri' ? 'Friday' : 'Saturday'}
              className="p-2 text-center text-sm font-medium text-muted-foreground border-b border-r border-border bg-muted/50"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar cells */}
        <div
          role="rowgroup"
          className={cn(
            'grid grid-cols-7',
            loading && 'opacity-50 pointer-events-none'
          )}
        >
          {calendarDays.map((day, index) => (
            <CalendarCell
              key={day.dateString}
              day={day}
              onEventClick={onEventClick}
              onDayClick={onDayClick}
              isFocused={focusedIndex === index}
              onFocus={() => setFocusedIndex(index)}
              tabIndex={focusedIndex === null ? (index === getInitialFocusIndex() ? 0 : -1) : (focusedIndex === index ? 0 : -1)}
              onKeyDown={(e) => handleKeyDown(e, index)}
            />
          ))}
        </div>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50" role="status" aria-live="polite">
          <div className="text-sm text-muted-foreground">Loading events...</div>
        </div>
      )}

      {/* Screen reader instructions */}
      <div className="sr-only" aria-live="polite">
        Use arrow keys to navigate dates. Press Enter or Space to select a date.
        Press Page Up for previous month, Page Down for next month.
      </div>
    </div>
  )
}

export default EventCalendar
