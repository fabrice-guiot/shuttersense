/**
 * PipelineValidationTrend Component
 *
 * Line chart showing consistency metrics over time.
 *
 * Supports two modes:
 * - aggregated: Shows 4 fixed percentage series
 *   - Overall Consistency %
 *   - Black Box Archive Consistency %
 *   - Browsable Archive Consistency %
 *   - Overall Inconsistent %
 * - comparison: Shows stacked area chart per collection
 */

import { useMemo } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts'
import { TrendChart, formatChartDate, formatChartPercent } from './TrendChart'
import type { PipelineValidationTrendResponse } from '@/contracts/api/trends-api'

// Fixed colors for aggregated mode series
const SERIES_COLORS = {
  overall_consistency: '#22c55e', // Green for overall consistency
  black_box_consistency: '#6366f1', // Indigo for Black Box
  browsable_consistency: '#3b82f6', // Blue for Browsable
  overall_inconsistent: '#ef4444' // Red for inconsistent
}

// Colors for comparison mode (stacked area)
const CONSISTENCY_COLORS = {
  consistent: 'hsl(142, 76%, 36%)', // Green
  partial: 'hsl(45, 93%, 47%)', // Yellow/warning
  inconsistent: 'hsl(0, 84%, 60%)' // Red
}

interface PipelineValidationTrendProps {
  data: PipelineValidationTrendResponse | null
  loading?: boolean
  error?: string | null
  showRatios?: boolean
}

export function PipelineValidationTrend({
  data,
  loading = false,
  error = null,
  showRatios = true
}: PipelineValidationTrendProps) {
  // Transform data for chart based on mode
  const chartData = useMemo(() => {
    if (!data) return []

    if (data.mode === 'aggregated') {
      // AGGREGATED MODE: Use data_points directly
      if (!data.data_points || data.data_points.length === 0) return []

      return data.data_points.map((point) => ({
        date: point.date,
        overall_consistency: point.overall_consistency_pct,
        black_box_consistency: point.black_box_consistency_pct,
        browsable_consistency: point.browsable_consistency_pct,
        overall_inconsistent: point.overall_inconsistent_pct,
        total_images: point.total_images,
        collections_included: point.collections_included
      }))
    } else {
      // COMPARISON MODE
      if (!data.collections || data.collections.length === 0) return []

      // For single collection, show stacked area
      if (data.collections.length === 1) {
        return data.collections[0].data_points.map((point) => ({
          date: point.date,
          consistent: showRatios ? point.consistent_ratio : point.consistent_count,
          partial: showRatios ? point.partial_ratio : point.partial_count,
          inconsistent: showRatios ? point.inconsistent_ratio : point.inconsistent_count,
          pipeline_name: point.pipeline_name
        }))
      }

      // For multiple collections, aggregate by date
      const dateSet = new Set<string>()
      data.collections.forEach((collection) => {
        collection.data_points.forEach((point) => {
          dateSet.add(point.date)
        })
      })

      const sortedDates = Array.from(dateSet).sort()

      return sortedDates.map((date) => {
        const row: Record<string, string | number> = { date }

        data.collections.forEach((collection) => {
          const point = collection.data_points.find((p) => p.date === date)
          if (point) {
            row[`consistent_${collection.collection_id}`] = showRatios
              ? point.consistent_ratio
              : point.consistent_count
          }
        })

        return row
      })
    }
  }, [data, showRatios])

  const isEmpty =
    !data ||
    (data.mode === 'aggregated'
      ? data.data_points.length === 0
      : data.collections.length === 0) ||
    chartData.length === 0

  // AGGREGATED MODE: Line chart with 4 percentage series
  if (!isEmpty && data?.mode === 'aggregated') {
    return (
      <TrendChart
        title="Pipeline Consistency Trend"
        description="Aggregated consistency percentages across all collections"
        loading={loading}
        error={error}
        isEmpty={isEmpty}
        emptyMessage="Run Pipeline Validation on a collection to see trend data"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={formatChartDate}
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              tickFormatter={formatChartPercent}
              domain={[0, 100]}
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <Tooltip
              formatter={(value: number, name: string) => [formatChartPercent(value), name]}
              labelFormatter={(label: string) => new Date(label).toLocaleString()}
              contentStyle={{
                backgroundColor: 'hsl(var(--popover))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 'var(--radius)'
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="overall_consistency"
              name="Overall Consistency"
              stroke={SERIES_COLORS.overall_consistency}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={true}
            />
            <Line
              type="monotone"
              dataKey="black_box_consistency"
              name="Black Box Archive"
              stroke={SERIES_COLORS.black_box_consistency}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={true}
            />
            <Line
              type="monotone"
              dataKey="browsable_consistency"
              name="Browsable Archive"
              stroke={SERIES_COLORS.browsable_consistency}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={true}
            />
            <Line
              type="monotone"
              dataKey="overall_inconsistent"
              name="Inconsistent"
              stroke={SERIES_COLORS.overall_inconsistent}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </TrendChart>
    )
  }

  // COMPARISON MODE: Stacked area chart for single collection
  if (!isEmpty && data?.mode === 'comparison' && data?.collections.length === 1) {
    return (
      <TrendChart
        title="Pipeline Consistency Trend"
        description={showRatios ? 'Consistency ratio over time (%)' : 'File counts by status'}
        loading={loading}
        error={error}
        isEmpty={isEmpty}
        emptyMessage="Run Pipeline Validation on a collection to see trend data"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={formatChartDate}
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <YAxis
              tickFormatter={showRatios ? formatChartPercent : undefined}
              domain={showRatios ? [0, 100] : undefined}
              className="text-xs"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                showRatios ? formatChartPercent(value) : value.toString(),
                name.charAt(0).toUpperCase() + name.slice(1)
              ]}
              labelFormatter={(label: string) => new Date(label).toLocaleString()}
              contentStyle={{
                backgroundColor: 'hsl(var(--popover))',
                border: '1px solid hsl(var(--border))',
                borderRadius: 'var(--radius)'
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="consistent"
              name="Consistent"
              stackId="1"
              fill={CONSISTENCY_COLORS.consistent}
              stroke={CONSISTENCY_COLORS.consistent}
              fillOpacity={0.7}
              connectNulls={true}
            />
            <Area
              type="monotone"
              dataKey="partial"
              name="Partial"
              stackId="1"
              fill={CONSISTENCY_COLORS.partial}
              stroke={CONSISTENCY_COLORS.partial}
              fillOpacity={0.7}
              connectNulls={true}
            />
            <Area
              type="monotone"
              dataKey="inconsistent"
              name="Inconsistent"
              stackId="1"
              fill={CONSISTENCY_COLORS.inconsistent}
              stroke={CONSISTENCY_COLORS.inconsistent}
              fillOpacity={0.7}
              connectNulls={true}
            />
          </AreaChart>
        </ResponsiveContainer>
      </TrendChart>
    )
  }

  // COMPARISON MODE: Line chart for multiple collections (consistency ratio comparison)
  return (
    <TrendChart
      title="Pipeline Consistency Trend"
      description="Consistency ratio comparison across collections"
      loading={loading}
      error={error}
      isEmpty={isEmpty}
      emptyMessage="Run Pipeline Validation on a collection to see trend data"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            tickFormatter={formatChartDate}
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <YAxis
            tickFormatter={showRatios ? formatChartPercent : undefined}
            domain={showRatios ? [0, 100] : undefined}
            className="text-xs"
            tick={{ fill: 'hsl(var(--muted-foreground))' }}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              showRatios ? formatChartPercent(value) : value.toString(),
              name
            ]}
            labelFormatter={(label: string) => new Date(label).toLocaleString()}
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              border: '1px solid hsl(var(--border))',
              borderRadius: 'var(--radius)'
            }}
          />
          <Legend />
          {data?.collections?.map((collection, index) => (
            <Area
              key={collection.collection_id}
              type="monotone"
              dataKey={`consistent_${collection.collection_id}`}
              name={`${collection.collection_name} - Consistent`}
              fill={`hsl(${120 + index * 30}, 70%, 50%)`}
              stroke={`hsl(${120 + index * 30}, 70%, 40%)`}
              fillOpacity={0.5}
              connectNulls={true}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </TrendChart>
  )
}
