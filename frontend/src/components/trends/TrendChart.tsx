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
  Legend
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

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
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  })
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
}

export function BaseLineChart({
  data,
  xDataKey,
  lines,
  xAxisFormatter = formatChartDate,
  yAxisFormatter,
  tooltipFormatter
}: BaseLineChartProps) {
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
        <Tooltip
          formatter={tooltipFormatter}
          labelFormatter={(label: string) => new Date(label).toLocaleString()}
          contentStyle={{
            backgroundColor: 'hsl(var(--popover))',
            border: '1px solid hsl(var(--border))',
            borderRadius: 'var(--radius)'
          }}
        />
        <Legend />
        {lines.map((line, index) => (
          <Line
            key={line.dataKey}
            type={line.type || 'monotone'}
            dataKey={line.dataKey}
            name={line.name}
            stroke={line.color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            connectNulls={true}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
