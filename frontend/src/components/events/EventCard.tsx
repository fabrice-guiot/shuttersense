/**
 * EventCard Component
 *
 * Compact event display for calendar cells
 * Issue #39 - Calendar Events feature (Phase 4)
 *
 * Accessibility (Phase 13):
 * - ARIA labels for screen readers
 * - Proper role attributes for status indicators
 */

import { LucideIcon, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ICON_MAP } from '@/components/settings/CategoryForm'
import { LogisticsStatusBadges } from '@/components/events/LogisticsSection'
import type { Event, AttendanceStatus } from '@/contracts/api/event-api'

// ============================================================================
// Attendance Status Colors
// ============================================================================

const ATTENDANCE_COLORS: Record<AttendanceStatus, string> = {
  planned: 'bg-amber-500/80',   // Yellow
  attended: 'bg-emerald-500/80', // Green
  skipped: 'bg-red-500/80'       // Red
}

const ATTENDANCE_BORDER_COLORS: Record<AttendanceStatus, string> = {
  planned: 'border-l-amber-500',
  attended: 'border-l-emerald-500',
  skipped: 'border-l-red-500'
}

const ATTENDANCE_LABELS: Record<AttendanceStatus, string> = {
  planned: 'Planned',
  attended: 'Attended',
  skipped: 'Skipped'
}

// ============================================================================
// EventCard Component
// ============================================================================

interface EventCardProps {
  event: Event
  onClick?: (event: Event) => void
  compact?: boolean
  /** In compact mode, allow text to wrap (up to 3 lines) instead of truncating */
  expanded?: boolean
  className?: string
}

export const EventCard = ({
  event,
  onClick,
  compact = false,
  expanded = false,
  className
}: EventCardProps) => {
  // Get category icon component
  const CategoryIcon: LucideIcon | undefined = event.category?.icon
    ? ICON_MAP[event.category.icon]
    : undefined

  // Format time display
  const timeDisplay = event.is_all_day
    ? 'All day'
    : event.start_time
      ? event.start_time.slice(0, 5) // HH:MM
      : null

  // Series indicator
  const seriesIndicator = event.series_guid && event.sequence_number && event.series_total
    ? `${event.sequence_number}/${event.series_total}`
    : null

  // Location display for compact mode (in parentheses)
  const locationShort = event.location?.name || null

  // Full title with location for tooltip
  const fullTitle = locationShort
    ? `${event.title} (${locationShort})`
    : event.title

  // Build accessible label for screen readers
  const accessibleLabel = [
    event.title,
    event.category?.name && `Category: ${event.category.name}`,
    locationShort && `Location: ${locationShort}`,
    timeDisplay && `Time: ${timeDisplay}`,
    seriesIndicator && `Part ${event.sequence_number} of ${event.series_total}`,
    `Status: ${ATTENDANCE_LABELS[event.attendance]}`
  ].filter(Boolean).join(', ')

  // Compact mode - minimal display for small calendar cells
  if (compact) {
    // Expanded mode: allow wrapping up to 3 lines (for single-event days)
    if (expanded) {
      return (
        <button
          onClick={() => onClick?.(event)}
          aria-label={accessibleLabel}
          role="listitem"
          className={cn(
            'w-full text-left px-1.5 py-0.5 rounded text-xs transition-colors',
            'hover:bg-accent/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            'border-l-2',
            ATTENDANCE_BORDER_COLORS[event.attendance],
            className
          )}
          style={{
            backgroundColor: event.category?.color
              ? `${event.category.color}20` // 12% opacity
              : undefined
          }}
          title={fullTitle}
        >
          <span className="flex items-start gap-1">
            {CategoryIcon && (
              <CategoryIcon
                className="h-2.5 w-2.5 flex-shrink-0 mt-0.5"
                style={{ color: event.category?.color || undefined }}
              />
            )}
            <span className="line-clamp-3">
              {event.title}
              {locationShort && (
                <span className="text-muted-foreground"> ({locationShort})</span>
              )}
            </span>
          </span>
        </button>
      )
    }

    // Standard compact: single line with truncation
    return (
      <button
        onClick={() => onClick?.(event)}
        aria-label={accessibleLabel}
        role="listitem"
        className={cn(
          'w-full text-left px-1.5 py-0.5 rounded text-xs truncate transition-colors',
          'hover:bg-accent/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'border-l-2',
          ATTENDANCE_BORDER_COLORS[event.attendance],
          className
        )}
        style={{
          backgroundColor: event.category?.color
            ? `${event.category.color}20` // 12% opacity
            : undefined
        }}
        title={fullTitle}
      >
        <span className="flex items-center gap-1">
          {CategoryIcon && (
            <CategoryIcon
              className="h-2.5 w-2.5 flex-shrink-0"
              style={{ color: event.category?.color || undefined }}
            />
          )}
          <span className="truncate">
            {event.title}
            {locationShort && (
              <span className="text-muted-foreground"> ({locationShort})</span>
            )}
          </span>
        </span>
      </button>
    )
  }

  // Standard mode - full display
  return (
    <button
      onClick={() => onClick?.(event)}
      aria-label={accessibleLabel}
      role="listitem"
      className={cn(
        'w-full text-left p-2 rounded-md transition-colors',
        'hover:bg-accent/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'border-l-3',
        ATTENDANCE_BORDER_COLORS[event.attendance],
        className
      )}
      style={{
        backgroundColor: event.category?.color
          ? `${event.category.color}15` // 8% opacity
          : undefined
      }}
    >
      <div className="flex items-start gap-2">
        {/* Category Icon */}
        {CategoryIcon && (
          <div
            className="flex-shrink-0 mt-0.5 p-1 rounded"
            style={{
              backgroundColor: event.category?.color
                ? `${event.category.color}30` // 18% opacity
                : undefined
            }}
          >
            <CategoryIcon
              className="h-3.5 w-3.5"
              style={{ color: event.category?.color || undefined }}
            />
          </div>
        )}

        {/* Event Info */}
        <div className="flex-1 min-w-0">
          {/* Title Row */}
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium truncate">{event.title}</span>
            {seriesIndicator && (
              <span className="flex-shrink-0 text-[10px] px-1 py-0.5 rounded bg-muted text-muted-foreground">
                {seriesIndicator}
              </span>
            )}
          </div>

          {/* Time & Category Row */}
          <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
            {timeDisplay && <span>{timeDisplay}</span>}
            {event.category && (
              <>
                {timeDisplay && <span className="text-muted-foreground/50">·</span>}
                <span className="truncate">{event.category.name}</span>
              </>
            )}
          </div>

          {/* Location Row */}
          {event.location && (
            <div className="flex items-center gap-1 mt-0.5 text-xs text-muted-foreground">
              <MapPin className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">
                {event.location.name}
                {event.location.city && `, ${event.location.city}`}
              </span>
            </div>
          )}

          {/* Logistics Indicators */}
          <LogisticsStatusBadges
            data={{
              ticket_required: event.ticket_required,
              ticket_status: event.ticket_status,
              ticket_purchase_date: null,
              timeoff_required: event.timeoff_required,
              timeoff_status: event.timeoff_status,
              timeoff_booking_date: null,
              travel_required: event.travel_required,
              travel_status: event.travel_status,
              travel_booking_date: null,
              deadline_date: null,
            }}
            size="sm"
            className="mt-1"
          />
        </div>

        {/* Attendance Indicator */}
        <div
          role="img"
          aria-label={`Attendance status: ${ATTENDANCE_LABELS[event.attendance]}`}
          className={cn(
            'flex-shrink-0 w-2 h-2 rounded-full mt-1.5',
            ATTENDANCE_COLORS[event.attendance]
          )}
          title={`Attendance: ${ATTENDANCE_LABELS[event.attendance]}`}
        />
      </div>
    </button>
  )
}

// ============================================================================
// EventList Component (for day detail views)
// ============================================================================

interface EventListProps {
  events: Event[]
  onEventClick?: (event: Event) => void
  emptyMessage?: string
  className?: string
}

export const EventList = ({
  events,
  onEventClick,
  emptyMessage = 'No events',
  className
}: EventListProps) => {
  if (events.length === 0) {
    return (
      <div className={cn('text-sm text-muted-foreground text-center py-4', className)} role="status">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div
      role="list"
      aria-label={`${events.length} event${events.length !== 1 ? 's' : ''}`}
      className={cn('space-y-1', className)}
    >
      {events.map(event => (
        <EventCard
          key={event.guid}
          event={event}
          onClick={onEventClick}
        />
      ))}
    </div>
  )
}

export default EventCard
