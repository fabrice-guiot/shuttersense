/**
 * DimensionMicroBar Component
 *
 * Linearized radar chart: five colored segments whose **widths** are fixed by
 * the configured scoring weights. Within each segment the colored fill shows
 * the actual score (0-100) and the remaining space is `bg-muted`.
 *
 * This ensures cross-event comparison is stable — changing one dimension's
 * score never shifts the position of other segments.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 8, US6)
 * Issue #208 - Normalize DimensionMicroBar Segment Sizes
 */

import { cn } from '@/lib/utils'
import { CHART_COLORS } from '@/components/trends/TrendChart'
import { DIMENSIONS } from '@/components/events/EventRadarChart'
import type { EventScores, ScoringWeightsResponse } from '@/contracts/api/conflict-api'

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_WEIGHT = 20

/** Map score dimension keys → weight keys in ScoringWeightsResponse */
const DIMENSION_WEIGHT_MAP: Record<string, keyof ScoringWeightsResponse> = {
  venue_quality: 'weight_venue_quality',
  organizer_reputation: 'weight_organizer_reputation',
  performer_lineup: 'weight_performer_lineup',
  logistics_ease: 'weight_logistics_ease',
  readiness: 'weight_readiness',
}

// ============================================================================
// Types
// ============================================================================

interface DimensionMicroBarProps {
  scores: EventScores
  weights?: ScoringWeightsResponse
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function DimensionMicroBar({ scores, weights, className }: DimensionMicroBarProps) {
  // Resolve per-dimension weights (fallback to equal 20 each)
  const resolvedWeights = DIMENSIONS.map(dim => {
    const weightKey = DIMENSION_WEIGHT_MAP[dim.key]
    return weightKey && weights ? (weights[weightKey] ?? DEFAULT_WEIGHT) : DEFAULT_WEIGHT
  })

  const totalWeight = resolvedWeights.reduce((sum, w) => sum + w, 0) || (DEFAULT_WEIGHT * DIMENSIONS.length)

  return (
    <div
      className={cn('hidden sm:flex h-1.5 w-full rounded-full overflow-hidden', className)}
      role="img"
      aria-label="Score dimensions"
    >
      {DIMENSIONS.map((dim, i) => {
        const weight = resolvedWeights[i]
        const segmentWidth = (weight / totalWeight) * 100
        const score = scores[dim.key] || 0
        const fillWidth = Math.max(0, Math.min(100, score))
        const weightPct = Math.round(segmentWidth)

        return (
          <div
            key={dim.key}
            className="bg-muted overflow-hidden"
            style={{ width: `${segmentWidth}%` }}
            title={`${dim.label}: ${Math.round(score)} (${weightPct}% weight)`}
          >
            <div
              className="h-full transition-all"
              style={{ width: `${fillWidth}%`, backgroundColor: CHART_COLORS[i] }}
            />
          </div>
        )
      })}
    </div>
  )
}
