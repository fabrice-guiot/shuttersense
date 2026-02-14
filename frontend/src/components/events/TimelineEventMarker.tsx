/**
 * TimelineEventMarker Component
 *
 * Event row for the timeline planner showing composite score bar,
 * dimension micro-bar, event metadata, and expandable radar chart.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 8, US6)
 */

import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import { ChevronDown, ChevronRight, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ICON_MAP } from '@/components/settings/CategoryForm'
import { DimensionMicroBar } from './DimensionMicroBar'
import { EventRadarChart } from './EventRadarChart'
import { formatDate } from '@/utils/dateFormat'
import type { ScoredEvent } from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface TimelineEventMarkerProps {
  event: ScoredEvent
  onClick?: (event: ScoredEvent) => void
  className?: string
  focused?: boolean
}

export interface TimelineEventMarkerHandle {
  focus: () => void
  toggleExpand: () => void
  collapse: () => void
}

// ============================================================================
// Score threshold colors for composite rating bar
// ============================================================================

function scoreBarColor(score: number): string {
  if (score >= 75) return 'bg-success'
  if (score >= 35) return 'bg-amber-500'
  return 'bg-destructive'
}

// ============================================================================
// Component
// ============================================================================

export const TimelineEventMarker = forwardRef<TimelineEventMarkerHandle, TimelineEventMarkerProps>(
  function TimelineEventMarker({ event, onClick, className, focused }, ref) {
  const [expanded, setExpanded] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const score = Math.round(event.scores.composite)
  const barColor = scoreBarColor(score)
  const isSkipped = event.attendance === 'skipped'

  const categoryIcon = event.category?.icon
    ? ICON_MAP[event.category.icon]
    : undefined
  const CategoryIcon = categoryIcon ?? MapPin

  useImperativeHandle(ref, () => ({
    focus: () => buttonRef.current?.focus(),
    toggleExpand: () => setExpanded(prev => !prev),
    collapse: () => setExpanded(false),
  }))

  useEffect(() => {
    if (focused) {
      buttonRef.current?.focus()
    }
  }, [focused])

  return (
    <div className={cn('group relative', className)}>
      {/* Skipped indicator — red vertical bar on left edge */}
      {isSkipped && (
        <div
          className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full bg-destructive"
          title="Skipped"
        />
      )}

      {/* Main row */}
      <button
        ref={buttonRef}
        type="button"
        data-marker-guid={event.guid}
        className={cn(
          'w-full text-left flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
          isSkipped && 'opacity-60',
        )}
        onClick={() => {
          setExpanded(prev => !prev)
          onClick?.(event)
        }}
        aria-expanded={expanded}
      >
        {/* Expand chevron */}
        <span className="text-muted-foreground shrink-0">
          {expanded
            ? <ChevronDown className="h-4 w-4" />
            : <ChevronRight className="h-4 w-4" />
          }
        </span>

        {/* Category icon + color dot */}
        <span
          className="shrink-0 flex items-center justify-center h-6 w-6 rounded"
          style={event.category?.color ? { backgroundColor: `${event.category.color}22` } : undefined}
        >
          <CategoryIcon
            className="h-3.5 w-3.5"
            style={event.category?.color ? { color: event.category.color } : undefined}
          />
        </span>

        {/* Event info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-sm font-medium truncate min-w-0">{event.title}</span>
            {event.location && (
              <span className="hidden sm:flex items-center gap-1 text-xs text-muted-foreground min-w-0 truncate">
                <MapPin className="h-3 w-3 shrink-0" />
                <span className="truncate">{event.location.name}</span>
              </span>
            )}
            <span className="text-xs text-muted-foreground shrink-0">
              {formatDate(event.event_date)}
            </span>
          </div>

          {/* Score bar + micro-bar */}
          <div className="mt-1 flex items-center gap-2">
            {/* Composite score bar */}
            <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', barColor)}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground tabular-nums shrink-0 w-8 text-right">
              {score}
            </span>
          </div>

          {/* Dimension micro-bar (hidden on mobile) */}
          <DimensionMicroBar scores={event.scores} className="mt-0.5" />
        </div>
      </button>

      {/* Expanded radar chart */}
      {expanded && (
        <div className="pl-10 pr-3 pb-3">
          <EventRadarChart
            events={[{ label: event.title, scores: event.scores }]}
            height={240}
            colorDimensions
            className="max-w-sm"
          />
        </div>
      )}
    </div>
  )
})
