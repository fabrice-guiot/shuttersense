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
  /** Color axis labels to match dimension colors (use only for single-event charts) */
  colorDimensions?: boolean
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
// Custom Tick — colors each dimension label to match the DimensionMicroBar
// ============================================================================

function DimensionTick(props: Record<string, unknown>) {
  const { x, y, payload, textAnchor } = props as {
    x: number
    y: number
    payload: { value: string }
    textAnchor: 'start' | 'middle' | 'end'
  }
  const idx = DIMENSIONS.findIndex(d => d.label === payload.value)
  const color = idx >= 0 ? CHART_COLORS[idx] : 'hsl(var(--muted-foreground))'
  return (
    <text x={x} y={y} textAnchor={textAnchor} fill={color} fontSize={11} fontWeight={500}>
      {payload.value}
    </text>
  )
}

// ============================================================================
// Component
// ============================================================================

export function EventRadarChart({ events, height = 280, colorDimensions, className }: EventRadarChartProps) {
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
            tick={colorDimensions ? <DimensionTick /> : { fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
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
