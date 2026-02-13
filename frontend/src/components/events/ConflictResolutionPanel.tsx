/**
 * ConflictResolutionPanel Component
 *
 * Displays conflict groups as cards with event details and resolution actions.
 * Users can confirm one event (marking others as skipped) or defer the decision.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 4, US2)
 */

import { AlertTriangle, Check, Clock, MapPin, Plane, SkipForward } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useResolveConflict } from '@/hooks/useResolveConflict'
import type {
  ConflictGroup,
  ConflictType,
  ScoredEvent,
} from '@/contracts/api/conflict-api'

// ============================================================================
// Conflict Type Display
// ============================================================================

const CONFLICT_TYPE_LABELS: Record<ConflictType, string> = {
  time_overlap: 'Time Overlap',
  distance: 'Distance Conflict',
  travel_buffer: 'Travel Buffer',
}

const CONFLICT_TYPE_ICONS: Record<ConflictType, typeof AlertTriangle> = {
  time_overlap: Clock,
  distance: MapPin,
  travel_buffer: Plane,
}

// ============================================================================
// ConflictGroupCard Component
// ============================================================================

interface ConflictGroupCardProps {
  group: ConflictGroup
  onConfirmEvent: (groupId: string, confirmedGuid: string, otherGuids: string[]) => void
  resolving: boolean
}

function ConflictGroupCard({ group, onConfirmEvent, resolving }: ConflictGroupCardProps) {
  const isResolved = group.status === 'resolved'

  // Get unique conflict types in this group
  const conflictTypes = [...new Set(group.edges.map(e => e.conflict_type))]

  return (
    <div
      className={cn(
        'rounded-lg border p-3 space-y-3',
        isResolved
          ? 'border-dashed border-muted-foreground/30 opacity-60'
          : 'border-amber-500/30 bg-amber-500/5',
      )}
    >
      {/* Conflict type labels */}
      <div className="flex items-center gap-2 flex-wrap">
        {conflictTypes.map(type => {
          const Icon = CONFLICT_TYPE_ICONS[type]
          return (
            <span
              key={type}
              className={cn(
                'inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded',
                isResolved
                  ? 'bg-muted text-muted-foreground'
                  : 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
              )}
            >
              <Icon className="h-3 w-3" />
              {CONFLICT_TYPE_LABELS[type]}
            </span>
          )
        })}
        {isResolved && (
          <span className="text-xs text-muted-foreground italic">Resolved</span>
        )}
      </div>

      {/* Event cards with scores */}
      <div className="space-y-2">
        {group.events.map(event => (
          <ConflictEventRow
            key={event.guid}
            event={event}
            groupId={group.group_id}
            otherGuids={group.events.filter(e => e.guid !== event.guid).map(e => e.guid)}
            isResolved={isResolved}
            onConfirm={onConfirmEvent}
            resolving={resolving}
          />
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// ConflictEventRow Component
// ============================================================================

interface ConflictEventRowProps {
  event: ScoredEvent
  groupId: string
  otherGuids: string[]
  isResolved: boolean
  onConfirm: (groupId: string, confirmedGuid: string, otherGuids: string[]) => void
  resolving: boolean
}

function ConflictEventRow({
  event,
  groupId,
  otherGuids,
  isResolved,
  onConfirm,
  resolving,
}: ConflictEventRowProps) {
  const isSkipped = event.attendance === 'skipped'

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-2 rounded-md',
        isSkipped ? 'opacity-50 bg-muted/30' : 'bg-card',
      )}
    >
      {/* Score badge */}
      <div
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold',
          event.scores.composite >= 70
            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
            : event.scores.composite >= 40
              ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
              : 'bg-red-500/15 text-red-600 dark:text-red-400',
        )}
        title={`Composite score: ${Math.round(event.scores.composite)}`}
      >
        {Math.round(event.scores.composite)}
      </div>

      {/* Event info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{event.title}</div>
        <div className="text-xs text-muted-foreground flex items-center gap-1.5">
          {event.start_time && <span>{event.start_time.slice(0, 5)}</span>}
          {event.start_time && event.end_time && <span>-</span>}
          {event.end_time && <span>{event.end_time.slice(0, 5)}</span>}
          {event.is_all_day && <span>All day</span>}
          {event.location && (
            <>
              <span className="text-muted-foreground/50">&middot;</span>
              <span className="truncate">{event.location.name}</span>
            </>
          )}
        </div>
      </div>

      {/* Action button */}
      {!isResolved && !isSkipped && (
        <Button
          variant="outline"
          size="sm"
          disabled={resolving}
          onClick={() => onConfirm(groupId, event.guid, otherGuids)}
          className="flex-shrink-0"
        >
          <Check className="h-3.5 w-3.5 mr-1" />
          Confirm
        </Button>
      )}
      {isSkipped && (
        <span className="flex-shrink-0 text-xs text-muted-foreground flex items-center gap-1">
          <SkipForward className="h-3 w-3" />
          Skipped
        </span>
      )}
    </div>
  )
}

// ============================================================================
// ConflictResolutionPanel Component
// ============================================================================

interface ConflictResolutionPanelProps {
  /** Conflict groups to display */
  groups: ConflictGroup[]
  /** Callback after successful resolution */
  onResolved?: () => void
  className?: string
}

export function ConflictResolutionPanel({
  groups,
  onResolved,
  className,
}: ConflictResolutionPanelProps) {
  const { resolve, loading } = useResolveConflict({ onSuccess: onResolved })

  const handleConfirmEvent = async (
    groupId: string,
    confirmedGuid: string,
    otherGuids: string[],
  ) => {
    try {
      await resolve({
        group_id: groupId,
        decisions: [
          { event_guid: confirmedGuid, attendance: 'planned' },
          ...otherGuids.map(guid => ({
            event_guid: guid,
            attendance: 'skipped' as const,
          })),
        ],
      })
    } catch {
      // Error state handled by the hook
    }
  }

  if (groups.length === 0) {
    return (
      <div className={cn('text-sm text-muted-foreground text-center py-4', className)}>
        No conflicts on this day
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      {groups.map(group => (
        <ConflictGroupCard
          key={group.group_id}
          group={group}
          onConfirmEvent={handleConfirmEvent}
          resolving={loading}
        />
      ))}
    </div>
  )
}
