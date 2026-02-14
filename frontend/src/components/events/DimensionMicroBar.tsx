/**
 * DimensionMicroBar Component
 *
 * Linearized radar chart: five colored segments proportional to dimension
 * scores rendered in a single horizontal bar. Hidden on mobile viewports.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 8, US6)
 */

import { cn } from '@/lib/utils'
import { CHART_COLORS } from '@/components/trends/TrendChart'
import { DIMENSIONS } from '@/components/events/EventRadarChart'
import type { EventScores } from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface DimensionMicroBarProps {
  scores: EventScores
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function DimensionMicroBar({ scores, className }: DimensionMicroBarProps) {
  const total = DIMENSIONS.reduce((sum, dim) => sum + (scores[dim.key] || 0), 0)

  return (
    <div
      className={cn('hidden sm:flex h-1.5 w-full rounded-full overflow-hidden bg-muted', className)}
      role="img"
      aria-label="Score dimensions"
    >
      {DIMENSIONS.map((dim, i) => {
        const value = scores[dim.key] || 0
        const pct = total > 0 ? (value / total) * 100 : 20
        return (
          <div
            key={dim.key}
            className="transition-all"
            style={{ width: `${pct}%`, backgroundColor: CHART_COLORS[i] }}
            title={`${dim.label}: ${Math.round(value)}`}
          />
        )
      })}
    </div>
  )
}
