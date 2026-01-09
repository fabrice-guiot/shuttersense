/**
 * TrendSummaryCard Component
 *
 * Displays trend summary with direction indicators
 */

import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { TrendSummaryResponse, TrendDirection } from '@/contracts/api/trends-api'
import { cn } from '@/lib/utils'

interface TrendSummaryCardProps {
  summary: TrendSummaryResponse | null
  loading?: boolean
  error?: string | null
}

const TREND_CONFIG: Record<
  TrendDirection,
  {
    icon: typeof TrendingUp
    color: string
    label: string
    bgColor: string
  }
> = {
  improving: {
    icon: TrendingUp,
    color: 'text-green-500',
    label: 'Improving',
    bgColor: 'bg-green-50 dark:bg-green-950/30'
  },
  stable: {
    icon: Minus,
    color: 'text-blue-500',
    label: 'Stable',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30'
  },
  degrading: {
    icon: TrendingDown,
    color: 'text-red-500',
    label: 'Degrading',
    bgColor: 'bg-red-50 dark:bg-red-950/30'
  },
  insufficient_data: {
    icon: AlertCircle,
    color: 'text-muted-foreground',
    label: 'Need more data',
    bgColor: 'bg-muted/50'
  }
}

function TrendIndicator({
  direction,
  label
}: {
  direction: TrendDirection
  label: string
}) {
  const config = TREND_CONFIG[direction]
  const Icon = config.icon

  return (
    <div className={cn('flex items-center gap-3 p-3 rounded-lg', config.bgColor)}>
      <Icon className={cn('h-5 w-5', config.color)} />
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className={cn('text-xs', config.color)}>{config.label}</div>
      </div>
    </div>
  )
}

export function TrendSummaryCard({ summary, loading = false, error = null }: TrendSummaryCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trend Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-24">
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
          <CardTitle>Trend Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive text-sm">{error}</div>
        </CardContent>
      </Card>
    )
  }

  if (!summary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trend Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground text-sm">No trend data available</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Trend Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <TrendIndicator direction={summary.orphaned_trend} label="Orphaned Files" />
          <TrendIndicator direction={summary.consistency_trend} label="Consistency" />
        </div>

        <div className="grid grid-cols-3 gap-2 pt-2 border-t">
          <div className="text-center">
            <div className="text-xl font-semibold">
              {summary.data_points_available.photostats}
            </div>
            <div className="text-xs text-muted-foreground">PhotoStats</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-semibold">
              {summary.data_points_available.photo_pairing}
            </div>
            <div className="text-xs text-muted-foreground">Photo Pairing</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-semibold">
              {summary.data_points_available.pipeline_validation}
            </div>
            <div className="text-xs text-muted-foreground">Pipeline Val.</div>
          </div>
        </div>

        {(summary.last_photostats || summary.last_photo_pairing || summary.last_pipeline_validation) && (
          <div className="text-xs text-muted-foreground pt-2 border-t">
            {summary.last_photostats && (
              <div>
                Last PhotoStats: {new Date(summary.last_photostats).toLocaleDateString()}
              </div>
            )}
            {summary.last_photo_pairing && (
              <div>
                Last Photo Pairing: {new Date(summary.last_photo_pairing).toLocaleDateString()}
              </div>
            )}
            {summary.last_pipeline_validation && (
              <div>
                Last Pipeline Val.:{' '}
                {new Date(summary.last_pipeline_validation).toLocaleDateString()}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
