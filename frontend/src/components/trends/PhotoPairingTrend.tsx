/**
 * PhotoPairingTrend Component
 *
 * Line chart showing image groups and total images over time.
 *
 * Supports two modes:
 * - aggregated: Shows 2 fixed series (Image Groups, Total Images)
 * - comparison: Shows per-collection series for up to 5 collections
 *
 * Note: Camera breakdown is NOT shown in aggregated mode (cameras differ per collection)
 */

import { useMemo } from 'react'
import {
  TrendChart,
  BaseLineChart,
  CHART_COLORS,
  formatChartDate,
  formatChartNumber
} from './TrendChart'
import type { PhotoPairingTrendResponse } from '@/contracts/api/trends-api'

// Fixed colors for aggregated mode series
const SERIES_COLORS = {
  group_count: '#6366f1', // Indigo for image groups
  image_count: '#22c55e' // Green for total images
}

interface PhotoPairingTrendProps {
  data: PhotoPairingTrendResponse | null
  loading?: boolean
  error?: string | null
  showCameraBreakdown?: boolean
}

export function PhotoPairingTrend({
  data,
  loading = false,
  error = null,
  showCameraBreakdown = true
}: PhotoPairingTrendProps) {
  // Transform data for chart based on mode
  const chartData = useMemo(() => {
    if (!data) return []

    if (data.mode === 'aggregated') {
      // AGGREGATED MODE: Use data_points directly
      if (!data.data_points || data.data_points.length === 0) return []

      return data.data_points.map((point) => ({
        date: point.date,
        group_count: point.group_count,
        image_count: point.image_count,
        collections_included: point.collections_included
      }))
    } else {
      // COMPARISON MODE: Build multi-collection data
      if (!data.collections || data.collections.length === 0) return []

      // For single collection with camera breakdown
      if (data.collections.length === 1 && showCameraBreakdown) {
        return data.collections[0].data_points.map((point) => {
          const row: Record<string, string | number> = {
            date: point.date,
            group_count: point.group_count,
            image_count: point.image_count
          }

          // Add camera usage fields
          Object.entries(point.camera_usage).forEach(([camera, count]) => {
            row[`camera_${camera}`] = count
          })

          return row
        })
      }

      // For multiple collections
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
            row[`groups_${collection.collection_id}`] = point.group_count
            row[`images_${collection.collection_id}`] = point.image_count
          }
        })

        return row
      })
    }
  }, [data, showCameraBreakdown])

  // Build lines configuration based on mode
  const lines = useMemo(() => {
    if (!data) return []

    if (data.mode === 'aggregated') {
      // AGGREGATED MODE: Fixed 2 series
      return [
        {
          dataKey: 'group_count',
          name: 'Image Groups',
          color: SERIES_COLORS.group_count
        },
        {
          dataKey: 'image_count',
          name: 'Total Images',
          color: SERIES_COLORS.image_count
        }
      ]
    } else {
      // COMPARISON MODE
      // For single collection with camera breakdown
      if (data.collections.length === 1 && showCameraBreakdown) {
        const collection = data.collections[0]
        const lineConfigs: Array<{
          dataKey: string
          name: string
          color: string
        }> = []

        // Add lines for each camera
        collection.cameras.forEach((camera, index) => {
          lineConfigs.push({
            dataKey: `camera_${camera}`,
            name: `Camera ${camera}`,
            color: CHART_COLORS[index % CHART_COLORS.length]
          })
        })

        return lineConfigs
      }

      // For multiple collections
      const lineConfigs: Array<{
        dataKey: string
        name: string
        color: string
      }> = []

      data.collections.forEach((collection, index) => {
        lineConfigs.push({
          dataKey: `images_${collection.collection_id}`,
          name: `${collection.collection_name} - Images`,
          color: CHART_COLORS[index % CHART_COLORS.length]
        })
      })

      return lineConfigs
    }
  }, [data, showCameraBreakdown])

  const isEmpty =
    !data ||
    (data.mode === 'aggregated'
      ? data.data_points.length === 0
      : data.collections.length === 0) ||
    chartData.length === 0

  const description =
    data?.mode === 'aggregated'
      ? 'Aggregated image groups and images across all collections'
      : data?.collections?.length === 1 && showCameraBreakdown
        ? 'Camera usage breakdown over time'
        : 'Compare image counts between selected collections'

  return (
    <TrendChart
      title="Photo Pairing Trend"
      description={description}
      loading={loading}
      error={error}
      isEmpty={isEmpty}
      emptyMessage="Run Photo Pairing on a collection to see trend data"
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
