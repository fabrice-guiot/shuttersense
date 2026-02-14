/**
 * EventRadarChart Component
 *
 * Recharts RadarChart wrapper that visualizes event quality scores across
 * five dimensions. Supports overlaying multiple events with distinct colors.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 5, US3)
 */

import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  Legend,
} from 'recharts'
import { CHART_COLORS } from '@/components/trends/TrendChart'
import type { EventScores } from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface EventOverlay {
  label: string
  scores: EventScores
}

interface EventRadarChartProps {
  /** One or more events to overlay on the chart */
  events: EventOverlay[]
  /** Chart height in pixels (default: 280) */
  height?: number
  className?: string
}

// ============================================================================
// Dimension Config
// ============================================================================

const DIMENSIONS: { key: keyof Omit<EventScores, 'composite'>; label: string }[] = [
  { key: 'venue_quality', label: 'Venue' },
  { key: 'organizer_reputation', label: 'Organizer' },
  { key: 'performer_lineup', label: 'Performers' },
  { key: 'logistics_ease', label: 'Logistics' },
  { key: 'readiness', label: 'Readiness' },
]

// ============================================================================
// Component
// ============================================================================

export function EventRadarChart({ events, height = 280, className }: EventRadarChartProps) {
  // Transform scores into Recharts data format
  const data = DIMENSIONS.map(dim => {
    const point: Record<string, string | number> = { dimension: dim.label }
    events.forEach((event, i) => {
      point[`event_${i}`] = Math.round(event.scores[dim.key])
    })
    return point
  })

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
            tickCount={6}
          />
          {events.map((event, i) => (
            <Radar
              key={i}
              name={event.label}
              dataKey={`event_${i}`}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              fillOpacity={events.length > 1 ? 0.15 : 0.25}
              strokeWidth={2}
            />
          ))}
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: 'var(--radius)',
              fontSize: 12,
            }}
          />
          {events.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 12 }}
            />
          )}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export { DIMENSIONS }
export type { EventOverlay }
