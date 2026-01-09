/**
 * PhotoStatsTrend Component
 *
 * Line chart showing orphaned files over time.
 *
 * Supports two modes:
 * - aggregated: Shows 2 fixed series (Orphaned Images, Orphaned Metadata)
 * - comparison: Shows per-collection series for up to 5 collections
 */

import { useMemo } from 'react'
import {
  TrendChart,
  BaseLineChart,
  CHART_COLORS,
  METRIC_COLORS,
  formatChartDate,
  formatChartNumber
} from './TrendChart'
import type { PhotoStatsTrendResponse } from '@/contracts/api/trends-api'

// Fixed colors for aggregated mode series
const SERIES_COLORS = {
  orphaned_images: '#ef4444', // Red for orphaned images
  orphaned_metadata: '#f59e0b' // Amber for orphaned metadata (XMP)
}

interface PhotoStatsTrendProps {
  data: PhotoStatsTrendResponse | null
  loading?: boolean
  error?: string | null
  selectedCollections?: number[]
}

export function PhotoStatsTrend({
  data,
  loading = false,
  error = null,
  selectedCollections
}: PhotoStatsTrendProps) {
  // Transform data for chart based on mode
  const chartData = useMemo(() => {
    if (!data) return []

    if (data.mode === 'aggregated') {
      // AGGREGATED MODE: Use data_points directly
      if (!data.data_points || data.data_points.length === 0) return []

      return data.data_points.map((point) => ({
        date: point.date,
        orphaned_images: point.orphaned_images,
        orphaned_metadata: point.orphaned_metadata,
        collections_included: point.collections_included
      }))
    } else {
      // COMPARISON MODE: Build multi-collection data
      if (!data.collections || data.collections.length === 0) return []

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
            row[`orphaned_images_${collection.collection_id}`] = point.orphaned_images_count
            row[`orphaned_xmp_${collection.collection_id}`] = point.orphaned_xmp_count
          }
        })

        return row
      })
    }
  }, [data])

  // Build lines configuration based on mode
  const lines = useMemo(() => {
    if (!data) return []

    if (data.mode === 'aggregated') {
      // AGGREGATED MODE: Fixed 2 series
      return [
        {
          dataKey: 'orphaned_images',
          name: 'Orphaned Images',
          color: SERIES_COLORS.orphaned_images
        },
        {
          dataKey: 'orphaned_metadata',
          name: 'Orphaned Metadata (XMP)',
          color: SERIES_COLORS.orphaned_metadata
        }
      ]
    } else {
      // COMPARISON MODE: Per-collection series
      const lineConfigs: Array<{
        dataKey: string
        name: string
        color: string
      }> = []

      data.collections.forEach((collection, index) => {
        const colorIndex = index % CHART_COLORS.length

        lineConfigs.push({
          dataKey: `orphaned_images_${collection.collection_id}`,
          name: `${collection.collection_name} - Orphaned Images`,
          color: CHART_COLORS[colorIndex]
        })

        // Add XMP line if we have data points with XMP orphans
        const hasXmpOrphans = collection.data_points.some((p) => p.orphaned_xmp_count > 0)
        if (hasXmpOrphans) {
          lineConfigs.push({
            dataKey: `orphaned_xmp_${collection.collection_id}`,
            name: `${collection.collection_name} - Orphaned XMP`,
            color: METRIC_COLORS.warning
          })
        }
      })

      return lineConfigs
    }
  }, [data])

  const isEmpty =
    !data ||
    (data.mode === 'aggregated'
      ? data.data_points.length === 0
      : data.collections.length === 0) ||
    chartData.length === 0

  const description =
    data?.mode === 'aggregated'
      ? 'Aggregated orphaned files across all collections'
      : 'Compare orphaned files between selected collections'

  return (
    <TrendChart
      title="Orphaned Files Trend"
      description={description}
      loading={loading}
      error={error}
      isEmpty={isEmpty}
      emptyMessage="Run PhotoStats on a collection to see trend data"
    >
      <BaseLineChart
        data={chartData}
        xDataKey="date"
        lines={lines}
        xAxisFormatter={formatChartDate}
        yAxisFormatter={formatChartNumber}
        tooltipFormatter={(value, name) => [formatChartNumber(value), name]}
      />
    </TrendChart>
  )
}
