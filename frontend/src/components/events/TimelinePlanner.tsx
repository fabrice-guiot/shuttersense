/**
 * TimelinePlanner Component
 *
 * Scrollable chronological timeline grouped by month with score bars,
 * conflict connectors, and inline radar comparison.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 8, US6)
 */

import { useState, useMemo } from 'react'
import { format, parseISO } from 'date-fns'
import { Filter, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TimelineEventMarker } from './TimelineEventMarker'
import { RadarComparisonDialog } from './RadarComparisonDialog'
import type {
  ScoredEvent,
  ConflictGroup,
  ConflictDetectionResponse,
} from '@/contracts/api/conflict-api'
import type { CategoryInfo } from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface TimelinePlannerProps {
  events: ScoredEvent[]
  conflicts: ConflictDetectionResponse | null
  loading?: boolean
  categories?: CategoryInfo[]
  onEventClick?: (event: ScoredEvent) => void
  onResolved?: () => void
  className?: string
}

type ConflictFilter = 'all' | 'conflicts_only' | 'unresolved_only'

// ============================================================================
// Helpers
// ============================================================================

/** Group events by month key (e.g. "2026-06") */
function groupByMonth(events: ScoredEvent[]): Map<string, ScoredEvent[]> {
  const groups = new Map<string, ScoredEvent[]>()
  for (const event of events) {
    const key = event.event_date.slice(0, 7) // "YYYY-MM"
    const list = groups.get(key) || []
    list.push(event)
    groups.set(key, list)
  }
  return groups
}

/** Format month key to display string */
function formatMonthLabel(monthKey: string): string {
  try {
    return format(parseISO(`${monthKey}-01`), 'MMMM yyyy')
  } catch {
    return monthKey
  }
}

/** Find which conflict group an event belongs to */
function findEventGroup(
  eventGuid: string,
  groups: ConflictGroup[],
): ConflictGroup | undefined {
  return groups.find(g => g.events.some(e => e.guid === eventGuid))
}

/** Build a set of event GUIDs that are in conflict groups */
function buildConflictedGuids(groups: ConflictGroup[]): Set<string> {
  const guids = new Set<string>()
  for (const g of groups) {
    for (const e of g.events) {
      guids.add(e.guid)
    }
  }
  return guids
}

// ============================================================================
// Conflict Connector
// ============================================================================

interface ConflictConnectorProps {
  group: ConflictGroup
  onClick: () => void
}

function ConflictConnector({ group, onClick }: ConflictConnectorProps) {
  const isResolved = group.status === 'resolved'
  const edgeTypes = [...new Set(group.edges.map(e => e.conflict_type))]
  const label = edgeTypes
    .map(t => t.replace(/_/g, ' '))
    .join(', ')

  return (
    <button
      type="button"
      className={cn(
        'absolute left-3 w-0.5 rounded-full transition-colors',
        isResolved
          ? 'bg-muted-foreground/30 border border-dashed border-muted-foreground/40'
          : 'bg-amber-500',
      )}
      style={{ top: 0, bottom: 0 }}
      onClick={onClick}
      title={`Conflict: ${label} (click to compare)`}
      aria-label={`${isResolved ? 'Resolved' : 'Unresolved'} conflict: ${label}`}
    />
  )
}

// ============================================================================
// Component
// ============================================================================

export function TimelinePlanner({
  events,
  conflicts,
  loading = false,
  categories = [],
  onEventClick,
  onResolved,
  className,
}: TimelinePlannerProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [conflictFilter, setConflictFilter] = useState<ConflictFilter>('all')
  const [compareGroup, setCompareGroup] = useState<ConflictGroup | null>(null)

  const conflictGroups = conflicts?.conflict_groups ?? []
  const conflictedGuids = useMemo(
    () => buildConflictedGuids(conflictGroups),
    [conflictGroups],
  )

  // Apply filters
  const filteredEvents = useMemo(() => {
    let result = events

    // Category filter
    if (categoryFilter !== 'all') {
      result = result.filter(e => e.category?.guid === categoryFilter)
    }

    // Conflict filter
    if (conflictFilter === 'conflicts_only') {
      result = result.filter(e => conflictedGuids.has(e.guid))
    } else if (conflictFilter === 'unresolved_only') {
      const unresolvedGuids = new Set<string>()
      for (const g of conflictGroups) {
        if (g.status !== 'resolved') {
          g.events.forEach(e => unresolvedGuids.add(e.guid))
        }
      }
      result = result.filter(e => unresolvedGuids.has(e.guid))
    }

    return result
  }, [events, categoryFilter, conflictFilter, conflictedGuids, conflictGroups])

  const monthGroups = useMemo(() => groupByMonth(filteredEvents), [filteredEvents])

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="h-4 w-4 text-muted-foreground" />

        {/* Category filter */}
        {categories.length > 0 && (
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="h-8 text-sm w-40">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map(cat => (
                <SelectItem key={cat.guid} value={cat.guid}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Conflict filter */}
        <Select value={conflictFilter} onValueChange={v => setConflictFilter(v as ConflictFilter)}>
          <SelectTrigger className="h-8 text-sm w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All events</SelectItem>
            <SelectItem value="conflicts_only">Conflicts only</SelectItem>
            <SelectItem value="unresolved_only">Unresolved only</SelectItem>
          </SelectContent>
        </Select>

        {/* Conflict summary badge */}
        {conflicts && conflicts.summary.unresolved > 0 && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" />
            {conflicts.summary.unresolved} unresolved
          </span>
        )}
      </div>

      {/* Timeline */}
      {filteredEvents.length === 0 ? (
        <div className="text-center text-sm text-muted-foreground py-12">
          No events match the current filters
        </div>
      ) : (
        <div className="space-y-6">
          {[...monthGroups.entries()].map(([monthKey, monthEvents]) => (
            <div key={monthKey}>
              {/* Month header */}
              <h3 className="text-sm font-semibold text-muted-foreground mb-2 sticky top-0 bg-background/95 backdrop-blur-sm py-1 z-10">
                {formatMonthLabel(monthKey)}
                <span className="ml-2 text-xs font-normal">
                  ({monthEvents.length} event{monthEvents.length !== 1 ? 's' : ''})
                </span>
              </h3>

              {/* Event markers with conflict connectors */}
              <div className="space-y-0.5">
                {monthEvents.map(event => {
                  const group = findEventGroup(event.guid, conflictGroups)
                  // Show connector only on first event in group within this month
                  const isFirstInGroup = group
                    ? monthEvents.find(e => group.events.some(ge => ge.guid === e.guid))?.guid === event.guid
                    : false
                  const groupEventsInMonth = group
                    ? monthEvents.filter(e => group.events.some(ge => ge.guid === e.guid))
                    : []

                  return (
                    <div key={event.guid} className="relative">
                      {/* Conflict connector (left margin line linking group events) */}
                      {isFirstInGroup && group && groupEventsInMonth.length > 1 && (
                        <ConflictConnector
                          group={group}
                          onClick={() => setCompareGroup(group)}
                        />
                      )}

                      <div className={cn(
                        group ? 'ml-5' : 'ml-0',
                      )}>
                        <TimelineEventMarker
                          event={event}
                          onClick={() => onEventClick?.(event)}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Radar comparison dialog */}
      <RadarComparisonDialog
        open={compareGroup !== null}
        onOpenChange={open => { if (!open) setCompareGroup(null) }}
        group={compareGroup}
        onResolved={() => {
          setCompareGroup(null)
          onResolved?.()
        }}
      />
    </div>
  )
}
