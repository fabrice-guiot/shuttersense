/**
 * TrendChart Component
 *
 * Base trend chart component using Recharts with consistent styling
 */

import { ReactNode } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  TooltipProps
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { formatDate, formatDateTime } from '@/utils/dateFormat'
import { AlertCircle } from 'lucide-react'

// Chart color palette using CSS variables for theme consistency
export const CHART_COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))'
]

// Semantic colors for specific metrics
export const METRIC_COLORS = {
  success: 'hsl(var(--success))',
  warning: 'hsl(var(--warning))',
  destructive: 'hsl(var(--destructive))',
  muted: 'hsl(var(--muted-foreground))'
}

interface TrendChartProps {
  title: string
  description?: string
  children: ReactNode
  loading?: boolean
  error?: string | null
  emptyMessage?: string
  isEmpty?: boolean
}

export function TrendChart({
  title,
  description,
  children,
  loading = false,
  error = null,
  emptyMessage = 'No trend data available',
  isEmpty = false
}: TrendChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center h-[300px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-[300px] text-destructive">
            {error}
          </div>
        ) : isEmpty ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            {emptyMessage}
          </div>
        ) : (
          <div className="h-[300px]">{children}</div>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Utility functions for chart data formatting
// ============================================================================

/**
 * Format date for chart X-axis labels
 */
export function formatChartDate(dateStr: string): string {
  return formatDate(dateStr, { dateStyle: 'short' })
}

/**
 * Format number for chart tooltips
 */
export function formatChartNumber(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

/**
 * Format bytes for chart display
 */
export function formatChartBytes(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${bytes} B`
}

/**
 * Format percentage for chart display
 */
export function formatChartPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

// ============================================================================
// Custom Tooltip with Calculated Count Support (Issue #105)
// ============================================================================

interface AggregatedTooltipPayload {
  calculated_count?: number
  collections_included?: number
  [key: string]: unknown
}

interface CustomTooltipProps extends TooltipProps<number, string> {
  valueFormatter?: (value: number, name: string) => [string, string]
}

/**
 * Custom tooltip that shows "X of Y collections have actual data" when some
 * values are calculated (filled forward) rather than actual results.
 *
 * This implements Issue #105 visual distinction of calculated vs actual data.
 */
export function AggregatedTooltip({
  active,
  payload,
  label,
  valueFormatter = (v, n) => [v.toString(), n]
}: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  // Get calculated_count and collections_included from the first payload entry
  const dataPoint = payload[0]?.payload as AggregatedTooltipPayload | undefined
  const calculatedCount = dataPoint?.calculated_count ?? 0
  const collectionsIncluded = dataPoint?.collections_included ?? 0
  const actualCount = collectionsIncluded - calculatedCount

  const showCalculatedWarning = calculatedCount > 0 && collectionsIncluded > 0

  return (
    <div
      className="rounded-md border bg-popover p-3 text-sm shadow-md"
      style={{
        backgroundColor: 'hsl(var(--popover))',
        border: '1px solid hsl(var(--border))',
        borderRadius: 'var(--radius)'
      }}
    >
      {/* Date header */}
      <p className="mb-2 font-medium text-foreground">{formatDateTime(label)}</p>

      {/* Calculated data warning */}
      {showCalculatedWarning && (
        <div className="mb-2 flex items-center gap-1.5 rounded bg-warning/10 px-2 py-1 text-xs text-warning">
          <AlertCircle className="h-3 w-3" />
          <span>
            {actualCount} of {collectionsIncluded} collections have actual data
          </span>
        </div>
      )}

      {/* Value entries */}
      <div className="space-y-1">
        {payload.map((entry, index) => {
          if (entry.value === null || entry.value === undefined) return null
          const [formattedValue, formattedName] = valueFormatter(entry.value as number, entry.name || '')
          return (
            <div key={index} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-muted-foreground">{formattedName}</span>
              </span>
              <span className="font-medium">{formattedValue}</span>
            </div>
          )
        })}
      </div>

      {/* Collections included footer */}
      {collectionsIncluded > 0 && (
        <p className="mt-2 border-t border-border pt-2 text-xs text-muted-foreground">
          {collectionsIncluded} collection{collectionsIncluded !== 1 ? 's' : ''} included
          {calculatedCount > 0 && ` (${calculatedCount} filled forward)`}
        </p>
      )}
    </div>
  )
}

// ============================================================================
// Reusable Chart Components
// ============================================================================

interface BaseLineChartProps {
  data: any[]
  xDataKey: string
  lines: Array<{
    dataKey: string
    name: string
    color: string
    type?: 'monotone' | 'linear' | 'step'
  }>
  xAxisFormatter?: (value: string) => string
  yAxisFormatter?: (value: number) => string
  tooltipFormatter?: (value: number, name: string) => [string, string]
  /** Field name indicating if the point is a transition point (renders as diamond) */
  transitionFieldKey?: string
  /** Field name indicating if the point is a NO_CHANGE copy (renders as hollow circle) */
  noChangeFieldKey?: string
  /** Use aggregated tooltip with calculated_count support (Issue #105) */
  showAggregatedTooltip?: boolean
}

/**
 * Custom dot component that renders different shapes based on data point type:
 * - Transition points (has_transition=true): Diamond shape
 * - NO_CHANGE results (no_change_copy=true): Hollow circle
 * - Normal results: Filled circle
 *
 * This implements FR-040: Trend charts MUST visually distinguish Input State
 * transition points using different symbols (not colors).
 */
interface TransitionDotProps {
  cx: number
  cy: number
  stroke: string
  payload: Record<string, unknown>
  value?: number | null
  transitionFieldKey?: string
  noChangeFieldKey?: string
}

function TransitionDot({
  cx,
  cy,
  stroke,
  payload,
  value,
  transitionFieldKey,
  noChangeFieldKey
}: TransitionDotProps) {
  // Don't render dot for null/undefined values (days without data)
  if (value === null || value === undefined) {
    return null
  }

  const isTransition = transitionFieldKey && payload[transitionFieldKey] === true
  const isNoChange = noChangeFieldKey && payload[noChangeFieldKey] === true

  if (isTransition) {
    // Diamond shape for transition points
    return (
      <polygon
        points={`${cx},${cy - 5} ${cx + 5},${cy} ${cx},${cy + 5} ${cx - 5},${cy}`}
        fill={stroke}
        stroke={stroke}
        strokeWidth={1}
      />
    )
  }

  if (isNoChange) {
    // Hollow circle for NO_CHANGE results (stable period)
    return (
      <circle
        cx={cx}
        cy={cy}
        r={3}
        fill="hsl(var(--background))"
        stroke={stroke}
        strokeWidth={2}
      />
    )
  }

  // Default filled circle for normal results
  return <circle cx={cx} cy={cy} r={3} fill={stroke} stroke={stroke} strokeWidth={1} />
}

export function BaseLineChart({
  data,
  xDataKey,
  lines,
  xAxisFormatter = formatChartDate,
  yAxisFormatter,
  tooltipFormatter,
  transitionFieldKey,
  noChangeFieldKey,
  showAggregatedTooltip = false
}: BaseLineChartProps) {
  // Create a custom dot component that has access to the field keys
  const createCustomDot = (color: string) => {
    if (!transitionFieldKey && !noChangeFieldKey) {
      return { r: 3 }
    }
    return (props: {
      key?: string
      cx: number
      cy: number
      value?: number | null
      payload: Record<string, unknown>
    }) => {
      // Destructure key to pass it directly to JSX, not via spread
      const { key, ...rest } = props
      return (
        <TransitionDot
          key={key}
          {...rest}
          stroke={color}
          transitionFieldKey={transitionFieldKey}
          noChangeFieldKey={noChangeFieldKey}
        />
      )
    }
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey={xDataKey}
          tickFormatter={xAxisFormatter}
          className="text-xs"
          tick={{ fill: 'hsl(var(--muted-foreground))' }}
        />
        <YAxis
          tickFormatter={yAxisFormatter}
          className="text-xs"
          tick={{ fill: 'hsl(var(--muted-foreground))' }}
        />
        {showAggregatedTooltip ? (
          <Tooltip
            content={<AggregatedTooltip valueFormatter={tooltipFormatter} />}
          />
        ) : (
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(label: string) => formatDateTime(label)}
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              border: '1px solid hsl(var(--border))',
              borderRadius: 'var(--radius)'
            }}
          />
        )}
        <Legend />
        {lines.map((line) => (
          <Line
            key={line.dataKey}
            type={line.type || 'monotone'}
            dataKey={line.dataKey}
            name={line.name}
            stroke={line.color}
            strokeWidth={2}
            dot={createCustomDot(line.color)}
            activeDot={{ r: 5 }}
            connectNulls={true}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
