/**
 * RadarComparisonDialog Component
 *
 * Full-screen comparison dialog that overlays radar charts for conflicting
 * events, shows a dimension breakdown table, and allows resolution.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 5, US3)
 */

import { Check, Clock, MapPin, Plane, SkipForward, Users } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { CHART_COLORS } from '@/components/trends/TrendChart'
import { EventRadarChart, DIMENSIONS } from './EventRadarChart'
import { useResolveConflict } from '@/hooks/useResolveConflict'
import type { ConflictGroup, ScoredEvent } from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface RadarComparisonDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  group: ConflictGroup | null
  onResolved?: () => void
}

// ============================================================================
// Component
// ============================================================================

export function RadarComparisonDialog({
  open,
  onOpenChange,
  group,
  onResolved,
}: RadarComparisonDialogProps) {
  const { resolve, loading } = useResolveConflict({
    onSuccess: () => {
      onResolved?.()
      onOpenChange(false)
    },
  })

  if (!group) return null

  const isResolved = group.status === 'resolved'
  const events = group.events

  const handleConfirm = async (confirmedGuid: string) => {
    try {
      await resolve({
        group_id: group.group_id,
        decisions: events.map(e => ({
          event_guid: e.guid,
          attendance: e.guid === confirmedGuid ? 'planned' as const : 'skipped' as const,
        })),
      })
    } catch {
      // Error handled by hook
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Compare Events</DialogTitle>
          <DialogDescription>
            {events.length} conflicting events — {isResolved ? 'resolved' : 'choose which to attend'}
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto min-h-0 flex-1 space-y-4">
          {/* Radar Chart */}
          <EventRadarChart
            events={events.map(e => ({
              label: e.title,
              scores: e.scores,
            }))}
            height={260}
          />

          {/* Dimension Breakdown Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-1.5 px-2 font-medium text-muted-foreground">Dimension</th>
                  {events.map((event, i) => (
                    <th key={event.guid} className="text-right py-1.5 px-2 font-medium" style={{ color: CHART_COLORS[i % CHART_COLORS.length] }}>
                      {event.title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DIMENSIONS.map(dim => (
                  <tr key={dim.key} className="border-b border-border/50">
                    <td className="py-1.5 px-2 text-muted-foreground">{dim.label}</td>
                    {events.map(event => {
                      const val = Math.round(event.scores[dim.key])
                      return (
                        <td key={event.guid} className="text-right py-1.5 px-2 tabular-nums">
                          <span className={cn(
                            val >= 70 ? 'text-emerald-600 dark:text-emerald-400' :
                            val >= 40 ? 'text-amber-600 dark:text-amber-400' :
                            'text-red-600 dark:text-red-400',
                          )}>
                            {val}
                          </span>
                        </td>
                      )
                    })}
                  </tr>
                ))}
                {/* Composite row */}
                <tr className="font-medium">
                  <td className="py-1.5 px-2">Composite</td>
                  {events.map(event => (
                    <td key={event.guid} className="text-right py-1.5 px-2 tabular-nums">
                      {Math.round(event.scores.composite)}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          {/* Event Detail Cards */}
          <div className="grid gap-3 sm:grid-cols-2">
            {events.map((event, i) => (
              <EventDetailCard
                key={event.guid}
                event={event}
                color={CHART_COLORS[i % CHART_COLORS.length]}
                isResolved={isResolved}
                loading={loading}
                onConfirm={() => handleConfirm(event.guid)}
              />
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ============================================================================
// EventDetailCard
// ============================================================================

function EventDetailCard({
  event,
  color,
  isResolved,
  loading,
  onConfirm,
}: {
  event: ScoredEvent
  color: string
  isResolved: boolean
  loading: boolean
  onConfirm: () => void
}) {
  const isSkipped = event.attendance === 'skipped'

  return (
    <div
      className={cn(
        'rounded-lg border p-3 space-y-2',
        isSkipped && 'opacity-50',
      )}
      style={{ borderColor: color }}
    >
      <div className="flex items-center gap-2">
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="font-medium text-sm truncate">{event.title}</span>
      </div>

      <div className="text-xs text-muted-foreground space-y-0.5">
        {/* Time */}
        <div className="flex items-center gap-1.5">
          <Clock className="h-3 w-3" />
          {event.is_all_day ? (
            <span>All day</span>
          ) : (
            <span>
              {event.start_time?.slice(0, 5)}
              {event.end_time && ` – ${event.end_time.slice(0, 5)}`}
            </span>
          )}
        </div>

        {/* Location */}
        {event.location && (
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3" />
            <span className="truncate">
              {event.location.name}
              {event.location.city && `, ${event.location.city}`}
            </span>
          </div>
        )}

        {/* Organizer */}
        {event.organizer && (
          <div className="flex items-center gap-1.5">
            <Plane className="h-3 w-3" />
            <span className="truncate">{event.organizer.name}</span>
          </div>
        )}

        {/* Performers */}
        {event.performer_count > 0 && (
          <div className="flex items-center gap-1.5">
            <Users className="h-3 w-3" />
            <span>{event.performer_count} performer{event.performer_count !== 1 ? 's' : ''}</span>
          </div>
        )}
      </div>

      {/* Action */}
      {!isResolved && !isSkipped && (
        <Button
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={onConfirm}
          className="w-full h-7 text-xs"
        >
          <Check className="h-3 w-3 mr-1" />
          Confirm
        </Button>
      )}
      {isSkipped && (
        <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground py-1">
          <SkipForward className="h-3 w-3" />
          Skipped
        </div>
      )}
    </div>
  )
}
