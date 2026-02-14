/**
 * TimelinePlanner Component
 *
 * Scrollable chronological timeline with score bars,
 * conflict connectors, and inline radar comparison.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 8, US6)
 */

import { useState, useMemo, useRef, useCallback } from 'react'
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
import type { TimelineEventMarkerHandle } from './TimelineEventMarker'
import { RadarComparisonDialog } from './RadarComparisonDialog'
import type {
  ScoredEvent,
  ConflictGroup,
  ConflictDetectionResponse,
  ScoringWeightsResponse,
  CategoryInfo,
} from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface TimelinePlannerProps {
  events: ScoredEvent[]
  conflicts: ConflictDetectionResponse | null
  loading?: boolean
  categories?: CategoryInfo[]
  scoringWeights?: ScoringWeightsResponse
  onEventClick?: (event: ScoredEvent) => void
  onResolved?: () => void
  className?: string
}

type ConflictFilter = 'all' | 'conflicts_only' | 'unresolved_only'

// ============================================================================
// Helpers
// ============================================================================

/** Sort events chronologically by date */
function sortByDate(events: ScoredEvent[]): ScoredEvent[] {
  return [...events].sort((a, b) => a.event_date.localeCompare(b.event_date))
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
// Segment helpers
// ============================================================================

type EventSegment =
  | { type: 'group'; group: ConflictGroup; events: ScoredEvent[] }
  | { type: 'single'; event: ScoredEvent }

/**
 * Segment events into conflict-group runs and standalone events.
 * Consecutive events belonging to the same conflict group are bundled
 * so the connector bar can wrap the entire group.
 */
function segmentByConflictGroup(
  events: ScoredEvent[],
  conflictGroups: ConflictGroup[],
): EventSegment[] {
  const segments: EventSegment[] = []
  let currentGroupId: string | null = null
  let currentGroupEvents: ScoredEvent[] = []
  let currentGroup: ConflictGroup | null = null

  const flush = () => {
    if (currentGroup && currentGroupEvents.length > 0) {
      segments.push({ type: 'group', group: currentGroup, events: currentGroupEvents })
    }
    currentGroupId = null
    currentGroupEvents = []
    currentGroup = null
  }

  for (const event of events) {
    const group = findEventGroup(event.guid, conflictGroups)
    const groupId = group?.group_id ?? null

    if (groupId && groupId === currentGroupId) {
      currentGroupEvents.push(event)
    } else {
      flush()
      if (group) {
        currentGroupId = group.group_id
        currentGroup = group
        currentGroupEvents = [event]
      } else {
        segments.push({ type: 'single', event })
      }
    }
  }

  flush()
  return segments
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
  scoringWeights,
  onEventClick,
  onResolved,
  className,
}: TimelinePlannerProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [conflictFilter, setConflictFilter] = useState<ConflictFilter>('all')
  const [compareGroup, setCompareGroup] = useState<ConflictGroup | null>(null)

  const markerRefs = useRef<Map<string, TimelineEventMarkerHandle>>(new Map())

  const setMarkerRef = useCallback((guid: string, handle: TimelineEventMarkerHandle | null) => {
    if (handle) {
      markerRefs.current.set(guid, handle)
    } else {
      markerRefs.current.delete(guid)
    }
  }, [])

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
          for (const e of g.events) {
            unresolvedGuids.add(e.guid)
          }
        }
      }
      result = result.filter(e => unresolvedGuids.has(e.guid))
    }

    return result
  }, [events, categoryFilter, conflictFilter, conflictedGuids, conflictGroups])

  const sortedEvents = useMemo(() => sortByDate(filteredEvents), [filteredEvents])

  /** Keyboard navigation: ArrowUp/Down move focus, Enter toggles expand, Escape collapses */
  const handleTimelineKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!sortedEvents.length) return

    const guids = sortedEvents.map(ev => ev.guid)

    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      // Find currently focused marker by checking document.activeElement
      let currentIdx = -1
      for (let i = 0; i < guids.length; i++) {
        if (document.activeElement === document.querySelector(`[data-marker-guid="${guids[i]}"]`)) {
          currentIdx = i
          break
        }
      }
      let nextIdx: number
      if (currentIdx === -1) {
        nextIdx = e.key === 'ArrowDown' ? 0 : guids.length - 1
      } else {
        nextIdx = e.key === 'ArrowDown'
          ? Math.min(currentIdx + 1, guids.length - 1)
          : Math.max(currentIdx - 1, 0)
      }
      markerRefs.current.get(guids[nextIdx])?.focus()
    } else if (e.key === 'Escape') {
      for (const guid of guids) {
        markerRefs.current.get(guid)?.collapse()
      }
    }
  }, [sortedEvents])

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
      {sortedEvents.length === 0 ? (
        <div className="text-center text-sm text-muted-foreground py-12">
          No events match the current filters
        </div>
      ) : (
        <div
          className="space-y-0.5"
          role="list"
          aria-label="Timeline events"
          onKeyDown={handleTimelineKeyDown}
        >
          {segmentByConflictGroup(sortedEvents, conflictGroups).map((segment, segIdx) => {
            if (segment.type === 'single') {
              return (
                <div key={segment.event.guid} className="ml-5" role="listitem">
                  <TimelineEventMarker
                    ref={handle => setMarkerRef(segment.event.guid, handle)}
                    event={segment.event}
                    scoringWeights={scoringWeights}
                    onClick={() => onEventClick?.(segment.event)}
                  />
                </div>
              )
            }

            // Conflict group segment — wrapper provides positioning context
            // for the connector bar to span all grouped events
            return (
              <div key={`${segment.group.group_id}-${segIdx}`} className="relative">
                {segment.events.length > 1 && (
                  <ConflictConnector
                    group={segment.group}
                    onClick={() => setCompareGroup(segment.group)}
                  />
                )}
                {segment.events.map(event => (
                  <div key={event.guid} className="ml-5" role="listitem">
                    <TimelineEventMarker
                      ref={handle => setMarkerRef(event.guid, handle)}
                      event={event}
                      scoringWeights={scoringWeights}
                      onClick={() => onEventClick?.(event)}
                    />
                  </div>
                ))}
              </div>
            )
          })}
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
