/**
 * Report Storage Tab Component
 *
 * Displays storage metrics and optimization statistics for the Analytics page.
 * Shows cumulative metrics, real-time statistics, and derived insights.
 *
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import type { ComponentType } from 'react'
import { useEffect, useImperativeHandle, forwardRef } from 'react'
import { Database, Archive, Trash2, TrendingDown, FileText, HardDrive } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { useStorageStats } from '@/hooks/useStorageStats'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { formatBytes, formatPercentage, getTotalStorageUsed } from '@/contracts/api/analytics-api'

// ============================================================================
// KPI Card Component
// ============================================================================

interface KPICardProps {
  title: string
  value: string | number
  description?: string
  icon: ComponentType<{ className?: string }>
  trend?: 'positive' | 'negative' | 'neutral'
}

function KPICard({ title, value, description, icon: Icon, trend }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${
          trend === 'positive' ? 'text-green-600 dark:text-green-400' :
          trend === 'negative' ? 'text-red-600 dark:text-red-400' :
          ''
        }`}>
          {value}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export interface ReportStorageTabRef {
  refetch: () => void
}

export const ReportStorageTab = forwardRef<ReportStorageTabRef>(function ReportStorageTab(_, ref) {
  const { stats, loading, error, refetch } = useStorageStats()
  const { setStats } = useHeaderStats()

  // Expose refetch to parent via ref
  useImperativeHandle(ref, () => ({
    refetch
  }), [refetch])

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Reports', value: stats.total_results_retained },
        { label: 'Storage', value: formatBytes(getTotalStorageUsed(stats)) },
        { label: 'Dedup', value: formatPercentage(stats.deduplication_ratio) }
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  if (loading && !stats) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {stats && (
        <>
          {/* Current Storage Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Current Storage</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard
                title="Total Results"
                value={stats.total_results_retained.toLocaleString()}
                description="Analysis results retained in database"
                icon={FileText}
              />
              <KPICard
                title="Original Results"
                value={stats.original_results_retained.toLocaleString()}
                description="Results with full HTML reports"
                icon={Database}
              />
              <KPICard
                title="Deduplicated Copies"
                value={stats.copy_results_retained.toLocaleString()}
                description="NO_CHANGE results (no HTML stored)"
                icon={Archive}
                trend="positive"
              />
              <KPICard
                title="Protected Results"
                value={stats.preserved_results_count.toLocaleString()}
                description="Preserved per retention policy"
                icon={HardDrive}
              />
            </div>
          </div>

          {/* Storage Usage Section */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Storage Usage</CardTitle>
              <CardDescription>
                Breakdown of storage used by retained results
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>JSON Data</span>
                    <span className="font-medium">{formatBytes(stats.reports_retained_json_bytes)}</span>
                  </div>
                  <Progress
                    value={
                      getTotalStorageUsed(stats) > 0
                        ? (stats.reports_retained_json_bytes / getTotalStorageUsed(stats)) * 100
                        : 0
                    }
                    className="h-2"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>HTML Reports</span>
                    <span className="font-medium">{formatBytes(stats.reports_retained_html_bytes)}</span>
                  </div>
                  <Progress
                    value={
                      getTotalStorageUsed(stats) > 0
                        ? (stats.reports_retained_html_bytes / getTotalStorageUsed(stats)) * 100
                        : 0
                    }
                    className="h-2"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Total Storage</span>
                    <span className="font-bold">{formatBytes(getTotalStorageUsed(stats))}</span>
                  </div>
                  <Progress value={100} className="h-2" />
                </div>
              </div>

              {/* Deduplication Ratio */}
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">Deduplication Ratio</h4>
                    <p className="text-sm text-muted-foreground">
                      Percentage of results that are deduplicated copies
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {formatPercentage(stats.deduplication_ratio)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      ~{formatBytes(stats.storage_savings_bytes)} saved
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Cleanup Statistics Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Cleanup Statistics (All Time)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard
                title="Total Reports Generated"
                value={stats.total_reports_generated.toLocaleString()}
                description="Cumulative job completions"
                icon={FileText}
              />
              <KPICard
                title="Jobs Purged"
                value={(stats.completed_jobs_purged + stats.failed_jobs_purged).toLocaleString()}
                description={`${stats.completed_jobs_purged} completed, ${stats.failed_jobs_purged} failed`}
                icon={Trash2}
              />
              <KPICard
                title="Results Purged"
                value={(stats.completed_results_purged_original + stats.completed_results_purged_copy).toLocaleString()}
                description={`${stats.completed_results_purged_original} original, ${stats.completed_results_purged_copy} copies`}
                icon={Archive}
              />
              <KPICard
                title="Storage Freed"
                value={formatBytes(stats.estimated_bytes_purged)}
                description="Estimated bytes freed by cleanup"
                icon={TrendingDown}
                trend="positive"
              />
            </div>
          </div>

          {/* Detailed Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Detailed Breakdown</CardTitle>
              <CardDescription>
                Cumulative statistics since storage tracking began
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div className="space-y-1">
                  <div className="text-muted-foreground">Completed Jobs Purged</div>
                  <div className="font-medium">{stats.completed_jobs_purged.toLocaleString()}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-muted-foreground">Failed Jobs Purged</div>
                  <div className="font-medium">{stats.failed_jobs_purged.toLocaleString()}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-muted-foreground">Original Results Purged</div>
                  <div className="font-medium">{stats.completed_results_purged_original.toLocaleString()}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-muted-foreground">Copy Results Purged</div>
                  <div className="font-medium">{stats.completed_results_purged_copy.toLocaleString()}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
})

export default ReportStorageTab
