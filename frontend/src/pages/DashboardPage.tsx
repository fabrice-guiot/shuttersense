/**
 * Dashboard Page
 *
 * Main landing page showing an overview of photo collections, analytics,
 * trend health, queue status, and recent analysis activity.
 */

import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  FolderOpen,
  FileImage,
  HardDrive,
  BarChart3,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  CalendarClock,
  ChartNoAxesCombined,
  Workflow,
  Calendar,
  ArrowRight,
  ImageOff,
  Bot,
  Ticket,
  Briefcase,
  Car,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { TrendSummaryCard } from '@/components/trends'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { useCollectionStats } from '@/hooks/useCollections'
import { useResultStats } from '@/hooks/useResults'
import { useQueueStatus } from '@/hooks/useTools'
import { useTrendSummary } from '@/hooks/useTrends'
import { usePipelineStats } from '@/hooks/usePipelines'
import { useAgentPoolStatus } from '@/hooks/useAgentPoolStatus'
import { useRecentResults, useEventDashboardStats } from '@/hooks/useDashboard'
import { formatRelativeTime } from '@/utils/dateFormat'
import type { AnalysisResultSummary, ResultStatus } from '@/contracts/api/results-api'

// ============================================================================
// Constants
// ============================================================================

const TOOL_LABELS: Record<string, string> = {
  photostats: 'PhotoStats',
  photo_pairing: 'Photo Pairing',
  pipeline_validation: 'Pipeline Val.',
  collection_test: 'Collection Test',
  inventory_validate: 'Inv. Validation',
  inventory_import: 'Inv. Import',
}

const STATUS_CONFIG: Record<
  ResultStatus,
  { label: string; variant: 'success' | 'destructive' | 'secondary' | 'default' }
> = {
  COMPLETED: { label: 'Completed', variant: 'success' },
  FAILED: { label: 'Failed', variant: 'destructive' },
  CANCELLED: { label: 'Cancelled', variant: 'secondary' },
  NO_CHANGE: { label: 'No Change', variant: 'default' },
}

// ============================================================================
// KPI Card Component
// ============================================================================

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: typeof FolderOpen
  loading?: boolean
}

function KpiCard({ title, value, subtitle, icon: Icon, loading }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-8 w-24 animate-pulse rounded bg-muted" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Queue Overview Card
// ============================================================================

function QueueOverviewCard({
  queueStatus,
  agentCount,
  loading,
}: {
  queueStatus: {
    scheduled_count: number
    queued_count: number
    running_count: number
    completed_count: number
    failed_count: number
    cancelled_count: number
  } | null
  agentCount: number | null
  loading: boolean
}) {
  if (loading || !queueStatus) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Queue Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const items = [
    {
      icon: CalendarClock,
      label: 'Scheduled',
      value: queueStatus.scheduled_count,
      color: 'text-info',
    },
    {
      icon: Activity,
      label: 'Running',
      value: queueStatus.running_count,
      color: 'text-success',
    },
    {
      icon: Clock,
      label: 'Queued',
      value: queueStatus.queued_count,
      color: 'text-warning',
    },
    {
      icon: CheckCircle,
      label: 'Completed',
      value: queueStatus.completed_count,
      color: 'text-muted-foreground',
    },
    {
      icon: XCircle,
      label: 'Failed',
      value: queueStatus.failed_count,
      color: queueStatus.failed_count > 0 ? 'text-destructive' : 'text-muted-foreground',
    },
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Queue Overview</CardTitle>
          {agentCount !== null && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Bot className="h-3.5 w-3.5" />
              {agentCount} agent{agentCount !== 1 ? 's' : ''} online
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => {
          const ItemIcon = item.icon
          return (
            <div key={item.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ItemIcon className={`h-4 w-4 ${item.color}`} />
                <span className="text-sm">{item.label}</span>
              </div>
              <span className="text-sm font-semibold">{item.value}</span>
            </div>
          )
        })}
        <div className="pt-2 border-t">
          <Link to="/analytics?tab=runs">
            <Button variant="ghost" size="sm" className="w-full justify-between">
              View all jobs
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Recent Results Card
// ============================================================================

function RecentResultsCard({
  results,
  loading,
}: {
  results: AnalysisResultSummary[]
  loading: boolean
}) {
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Recent Analysis Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (results.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Recent Analysis Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <ImageOff className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground text-sm">No analysis results yet</p>
            <p className="text-muted-foreground text-xs mt-1">
              Run analysis tools from the{' '}
              <Link to="/analytics?tab=runs" className="underline hover:no-underline">
                Analytics
              </Link>{' '}
              page
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Recent Analysis Results</CardTitle>
          <Link to="/analytics?tab=reports">
            <Button variant="ghost" size="sm" className="gap-1">
              View all
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {results.map((result) => (
            <Link
              key={result.guid}
              to={`/analytics?tab=reports&id=${result.guid}`}
              className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">
                    {TOOL_LABELS[result.tool] || result.tool}
                  </div>
                  <div className="text-xs text-muted-foreground truncate">
                    {result.collection_name || 'System-wide'}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <Badge variant={STATUS_CONFIG[result.status].variant}>
                  {STATUS_CONFIG[result.status].label}
                </Badge>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatRelativeTime(result.completed_at)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Upcoming Events Card
// ============================================================================

function UpcomingEventsCard({
  stats,
  loading,
}: {
  stats: {
    upcoming_30d_count: number
    needs_tickets_count: number
    needs_pto_count: number
    needs_travel_count: number
  } | null
  loading: boolean
}) {
  if (loading || !stats) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Upcoming Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-24">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const items = [
    {
      icon: Calendar,
      label: 'Upcoming (30 days)',
      value: stats.upcoming_30d_count,
      href: '/events?preset=upcoming_30d',
      highlight: false,
    },
    {
      icon: Ticket,
      label: 'Needs Tickets',
      value: stats.needs_tickets_count,
      href: '/events?preset=needs_tickets',
      highlight: stats.needs_tickets_count > 0,
    },
    {
      icon: Briefcase,
      label: 'Needs PTO',
      value: stats.needs_pto_count,
      href: '/events?preset=needs_pto',
      highlight: stats.needs_pto_count > 0,
    },
    {
      icon: Car,
      label: 'Needs Travel',
      value: stats.needs_travel_count,
      href: '/events?preset=needs_travel',
      highlight: stats.needs_travel_count > 0,
    },
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Upcoming Events</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => {
          const ItemIcon = item.icon
          return (
            <Link
              key={item.label}
              to={item.href}
              className="flex items-center justify-between hover:bg-accent rounded-md px-2 py-1 -mx-2 transition-colors"
            >
              <div className="flex items-center gap-2">
                <ItemIcon className={`h-4 w-4 ${item.highlight ? 'text-destructive' : 'text-muted-foreground'}`} />
                <span className="text-sm">{item.label}</span>
              </div>
              <span className={`text-sm font-semibold ${item.highlight ? 'text-destructive' : ''}`}>
                {item.value}
              </span>
            </Link>
          )
        })}
        <div className="pt-2 border-t">
          <Link to="/events">
            <Button variant="ghost" size="sm" className="w-full justify-between">
              View calendar
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Quick Links Card
// ============================================================================

function QuickLinksCard() {
  const links = [
    {
      to: '/collections',
      icon: FolderOpen,
      label: 'Collections',
      description: 'Manage photo collections',
    },
    {
      to: '/analytics',
      icon: ChartNoAxesCombined,
      label: 'Analytics',
      description: 'Trends, reports, and tool runs',
    },
    {
      to: '/pipelines',
      icon: Workflow,
      label: 'Pipelines',
      description: 'Processing workflow definitions',
    },
    {
      to: '/events',
      icon: Calendar,
      label: 'Events',
      description: 'Photo event calendar',
    },
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Quick Links</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {links.map((link) => {
            const LinkIcon = link.icon
            return (
              <Link
                key={link.to}
                to={link.to}
                className="flex flex-col items-center gap-2 rounded-lg border p-4 hover:bg-accent transition-colors text-center"
              >
                <LinkIcon className="h-6 w-6 text-muted-foreground" />
                <div>
                  <div className="text-sm font-medium">{link.label}</div>
                  <div className="text-xs text-muted-foreground hidden sm:block">
                    {link.description}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Dashboard Page
// ============================================================================

export default function DashboardPage() {
  // Data hooks
  const { stats: collectionStats, loading: collectionsLoading } = useCollectionStats()
  const { stats: resultStats, loading: resultsLoading } = useResultStats()
  const { queueStatus, loading: queueLoading } = useQueueStatus()
  const { stats: pipelineStats, loading: pipelinesLoading } = usePipelineStats()
  const { poolStatus } = useAgentPoolStatus()
  const {
    summary: trendSummary,
    loading: summaryLoading,
    error: summaryError,
  } = useTrendSummary()
  const { results: recentResults, loading: recentLoading } = useRecentResults()
  const { stats: eventDashboardStats, loading: eventDashboardLoading } = useEventDashboardStats()

  // Header stats context
  const { setStats } = useHeaderStats()

  // Set header stats
  useEffect(() => {
    const statsArray: Array<{ label: string; value: string | number }> = []

    if (collectionStats) {
      statsArray.push({ label: 'Storage', value: collectionStats.storage_used_formatted })
      statsArray.push({ label: 'Images', value: collectionStats.image_count.toLocaleString() })
    }

    if (queueStatus) {
      statsArray.push({ label: 'Scheduled', value: queueStatus.scheduled_count })
    }

    if (queueStatus && queueStatus.running_count > 0) {
      statsArray.push({ label: 'Running', value: queueStatus.running_count })
    }

    setStats(statsArray)
    return () => setStats([])
  }, [collectionStats, queueStatus, setStats])

  return (
    <div className="flex flex-col gap-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Storage"
          value={collectionStats?.storage_used_formatted ?? '0 B'}
          subtitle={collectionStats ? `${collectionStats.total_collections} collection${collectionStats.total_collections !== 1 ? 's' : ''}` : undefined}
          icon={HardDrive}
          loading={collectionsLoading}
        />
        <KpiCard
          title="Images"
          value={collectionStats?.image_count.toLocaleString() ?? '0'}
          subtitle={collectionStats ? `${collectionStats.file_count.toLocaleString()} files total` : undefined}
          icon={FileImage}
          loading={collectionsLoading}
        />
        <KpiCard
          title="Analysis Results"
          value={resultStats?.total_results ?? 0}
          subtitle={
            resultStats
              ? `${resultStats.completed_count} completed, ${resultStats.failed_count} failed`
              : undefined
          }
          icon={BarChart3}
          loading={resultsLoading}
        />
        <KpiCard
          title="Pipelines"
          value={pipelineStats?.active_pipeline_count ?? 0}
          subtitle={
            pipelineStats
              ? `${pipelineStats.total_pipelines} total, ${pipelineStats.valid_pipelines} valid`
              : undefined
          }
          icon={Workflow}
          loading={pipelinesLoading}
        />
      </div>

      {/* Trend Summary */}
      <TrendSummaryCard
        summary={trendSummary}
        loading={summaryLoading}
        error={summaryError}
      />

      {/* Upcoming Events + Queue Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UpcomingEventsCard
          stats={eventDashboardStats}
          loading={eventDashboardLoading}
        />
        <QueueOverviewCard
          queueStatus={queueStatus}
          agentCount={poolStatus?.online_count ?? null}
          loading={queueLoading}
        />
      </div>

      {/* Recent Results */}
      <RecentResultsCard results={recentResults} loading={recentLoading} />

      {/* Quick Links */}
      <QuickLinksCard />
    </div>
  )
}
