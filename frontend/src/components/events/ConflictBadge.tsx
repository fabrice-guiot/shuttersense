/**
 * ConflictBadge Component
 *
 * Small indicator badge showing scheduling conflict status for an event.
 * Displays conflict type icon with tooltip describing the conflict.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 3, US1)
 */

import { AlertTriangle, Clock, MapPin, Plane } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import type { ConflictType, ConflictGroupStatus } from '@/contracts/api/conflict-api'

// ============================================================================
// Conflict Type Labels & Icons
// ============================================================================

const CONFLICT_TYPE_LABELS: Record<ConflictType, string> = {
  time_overlap: 'Time overlap',
  distance: 'Distance conflict',
  travel_buffer: 'Travel buffer conflict',
}

const CONFLICT_TYPE_ICONS: Record<ConflictType, typeof AlertTriangle> = {
  time_overlap: Clock,
  distance: MapPin,
  travel_buffer: Plane,
}

// ============================================================================
// ConflictBadge Component
// ============================================================================

export interface ConflictBadgeProps {
  /** Conflict edges involving this event */
  conflicts: Array<{
    type: ConflictType
    otherEventTitle: string
    detail: string
  }>
  /** Overall status of the conflict group */
  status: ConflictGroupStatus
  /** Compact mode: icon-only, tooltip on tap (mobile) */
  compact?: boolean
  className?: string
}

export function ConflictBadge({
  conflicts,
  status,
  compact = false,
  className,
}: ConflictBadgeProps) {
  if (conflicts.length === 0) return null

  const isResolved = status === 'resolved'

  // Use the first conflict type for the primary icon, or AlertTriangle for mixed
  const conflictTypes = new Set(conflicts.map(c => c.type))
  const primaryType = conflictTypes.size === 1
    ? conflicts[0].type
    : null
  const Icon = primaryType
    ? CONFLICT_TYPE_ICONS[primaryType]
    : AlertTriangle

  // Build tooltip lines
  const tooltipLines = conflicts.map(c =>
    `${CONFLICT_TYPE_LABELS[c.type]} with ${c.otherEventTitle}`
  )

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            role="img"
            aria-label={`Conflict: ${tooltipLines.join(', ')}`}
            className={cn(
              'inline-flex items-center justify-center',
              compact ? 'h-4 w-4' : 'h-5 gap-1 px-1.5 rounded',
              isResolved
                ? 'text-muted-foreground border border-dashed border-muted-foreground/50'
                : 'text-amber-600 dark:text-amber-400 bg-amber-500/15',
              !compact && !isResolved && 'border border-amber-500/30',
              className,
            )}
          >
            <Icon className={cn(compact ? 'h-3 w-3' : 'h-3.5 w-3.5')} />
            {!compact && conflicts.length > 1 && (
              <span className="text-[10px] font-medium">{conflicts.length}</span>
            )}
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-0.5">
            {tooltipLines.map((line, i) => (
              <div key={i} className="text-xs">{line}</div>
            ))}
            {isResolved && (
              <div className="text-xs text-muted-foreground italic">Resolved</div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
