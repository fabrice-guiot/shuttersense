/**
 * DisplayGraphTrend Component
 *
 * Displays aggregated pipeline path enumeration trends over time.
 * Shows trends for: Total Paths, Valid Paths, Black Box Archive, Browsable Archive
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import type { DisplayGraphTrendResponse } from '@/contracts/api/trends-api'
import { formatChartDate } from './TrendChart'

interface DisplayGraphTrendProps {
  data: DisplayGraphTrendResponse | null
  loading?: boolean
  error?: string | null
}

// Fixed colors for each series
const SERIES_COLORS = {
  total_paths: '#6366f1',           // Indigo
  valid_paths: '#22c55e',           // Green
  black_box_archive_paths: '#f59e0b', // Amber
  browsable_archive_paths: '#3b82f6'  // Blue
}

export function DisplayGraphTrend({
  data,
  loading = false,
  error = null
}: DisplayGraphTrendProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Graph Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Graph Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.data_points.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Graph Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">
            No display-graph results available for the selected filters
          </div>
        </CardContent>
      </Card>
    )
  }

  // Transform data for chart
  const chartData = data.data_points.map((point) => ({
    date: formatChartDate(point.date),
    total_paths: point.total_paths,
    valid_paths: point.valid_paths,
    black_box_archive_paths: point.black_box_archive_paths,
    browsable_archive_paths: point.browsable_archive_paths
  }))

  // Calculate summary stats from the latest data point
  const latestPoint = data.data_points[data.data_points.length - 1]
  const summaryStats = {
    totalPaths: latestPoint?.total_paths ?? 0,
    validPaths: latestPoint?.valid_paths ?? 0,
    blackBoxArchive: latestPoint?.black_box_archive_paths ?? 0,
    browsableArchive: latestPoint?.browsable_archive_paths ?? 0
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Graph Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-muted rounded-lg p-3">
            <div className="text-xs text-muted-foreground mb-1">Total Paths</div>
            <div className="text-2xl font-bold" style={{ color: SERIES_COLORS.total_paths }}>
              {summaryStats.totalPaths}
            </div>
          </div>
          <div className="bg-muted rounded-lg p-3">
            <div className="text-xs text-muted-foreground mb-1">Valid Paths</div>
            <div className="text-2xl font-bold" style={{ color: SERIES_COLORS.valid_paths }}>
              {summaryStats.validPaths}
            </div>
          </div>
          <div className="bg-muted rounded-lg p-3">
            <div className="text-xs text-muted-foreground mb-1">Black Box Archive</div>
            <div className="text-2xl font-bold" style={{ color: SERIES_COLORS.black_box_archive_paths }}>
              {summaryStats.blackBoxArchive}
            </div>
          </div>
          <div className="bg-muted rounded-lg p-3">
            <div className="text-xs text-muted-foreground mb-1">Browsable Archive</div>
            <div className="text-2xl font-bold" style={{ color: SERIES_COLORS.browsable_archive_paths }}>
              {summaryStats.browsableArchive}
            </div>
          </div>
        </div>

        {/* Pipelines included */}
        {data.pipelines_included.length > 0 && (
          <div className="text-xs text-muted-foreground">
            Aggregating data from: {data.pipelines_included.map((p) => p.pipeline_name).join(', ')}
            {' '}({data.pipelines_included.reduce((sum, p) => sum + p.result_count, 0)} results)
          </div>
        )}

        {/* Chart */}
        {chartData.length > 1 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  className="text-muted-foreground"
                />
                <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    borderColor: 'hsl(var(--border))',
                    borderRadius: '0.5rem'
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total_paths"
                  name="Total Paths"
                  stroke={SERIES_COLORS.total_paths}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  connectNulls={true}
                />
                <Line
                  type="monotone"
                  dataKey="valid_paths"
                  name="Valid Paths"
                  stroke={SERIES_COLORS.valid_paths}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  connectNulls={true}
                />
                <Line
                  type="monotone"
                  dataKey="black_box_archive_paths"
                  name="Black Box Archive"
                  stroke={SERIES_COLORS.black_box_archive_paths}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  connectNulls={true}
                />
                <Line
                  type="monotone"
                  dataKey="browsable_archive_paths"
                  name="Browsable Archive"
                  stroke={SERIES_COLORS.browsable_archive_paths}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                  connectNulls={true}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-4 text-sm">
            Need more data points to display trend chart
          </div>
        )}
      </CardContent>
    </Card>
  )
}
