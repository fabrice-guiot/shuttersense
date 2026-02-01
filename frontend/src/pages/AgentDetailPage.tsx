/**
 * AgentDetailPage Component
 *
 * Displays detailed information about a single agent including:
 * - System metrics (CPU, memory, disk)
 * - Job statistics and recent job history
 * - Bound collections count
 * - Real-time status updates
 *
 * Issue #90 - Distributed Agent Architecture (Phase 11)
 * Task: T174 - Create AgentDetailPage
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  RefreshCw,
  Loader2,
  Cpu,
  HardDrive,
  CheckCircle,
  XCircle,
  AlertCircle,
  FolderOpen,
  Activity,
  Clock,
  Server,
  Monitor,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { useAgentDetail, useAgentJobHistory } from '@/hooks/useAgentDetail'
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge'
import { GuidBadge } from '@/components/GuidBadge'
import { formatDateTime, formatRelativeTime } from '@/utils/dateFormat'
import { AuditTrailSection } from '@/components/audit'
import type { AgentJobHistoryItem } from '@/contracts/api/agent-api'

// ============================================================================
// Helper Components
// ============================================================================

/**
 * Metric card for displaying system metrics
 */
function MetricCard({
  title,
  icon: Icon,
  value,
  unit,
  percentage,
}: {
  title: string
  icon: React.ElementType
  value: number | string | null
  unit?: string
  percentage?: number | null
}) {
  const hasValue = value !== null && value !== undefined

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-muted p-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {hasValue ? (
              <div>
                <p className="text-2xl font-bold">
                  {value}
                  {unit && <span className="text-sm font-normal text-muted-foreground"> {unit}</span>}
                </p>
                {percentage !== null && percentage !== undefined && (
                  <div className="mt-2 h-1.5 w-full bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${Math.min(100, percentage)}%` }}
                    />
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No data</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Stat card for displaying job statistics
 */
function StatCard({
  title,
  icon: Icon,
  value,
  iconColor,
}: {
  title: string
  icon: React.ElementType
  value: number
  iconColor?: string
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-muted p-2">
            <Icon className={`h-5 w-5 ${iconColor || 'text-muted-foreground'}`} />
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Job status badge
 */
function JobStatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    pending: 'secondary',
    assigned: 'secondary',
    running: 'default',
    completed: 'default',
    failed: 'destructive',
    cancelled: 'outline',
  }

  return (
    <Badge variant={variants[status] || 'secondary'} className="capitalize">
      {status}
    </Badge>
  )
}

// ============================================================================
// Job Table Columns
// ============================================================================

const jobColumns: ColumnDef<AgentJobHistoryItem>[] = [
  {
    header: 'Tool',
    cell: (job) => job.tool,
    cellClassName: 'font-medium',
    cardRole: 'title',
  },
  {
    header: 'Collection',
    cell: (job) =>
      job.collection_name ? (
        <Link
          to={`/collections/${job.collection_guid}`}
          className="text-primary hover:underline"
        >
          {job.collection_name}
        </Link>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    cardRole: 'subtitle',
  },
  {
    header: 'Status',
    cell: (job) => <JobStatusBadge status={job.status} />,
    cardRole: 'badge',
  },
  {
    header: 'Started',
    cell: (job) =>
      job.started_at ? (
        <span className="text-sm text-muted-foreground">
          {formatRelativeTime(job.started_at)}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    cardRole: 'detail',
  },
  {
    header: 'Completed',
    cell: (job) =>
      job.completed_at ? (
        <span className="text-sm text-muted-foreground">
          {formatRelativeTime(job.completed_at)}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
    cardRole: 'detail',
  },
]

// ============================================================================
// Main Component
// ============================================================================

export default function AgentDetailPage() {
  const { guid } = useParams<{ guid: string }>()
  const navigate = useNavigate()
  const { setStats } = useHeaderStats()

  // Fetch agent detail with real-time updates
  const { agent, loading, error, refetch, wsConnected } = useAgentDetail(guid || '', true, true)

  // Fetch job history (separate pagination)
  const {
    jobs,
    totalCount: totalJobs,
    loading: jobsLoading,
    fetchPage,
    offset: jobsOffset,
    limit: jobsLimit,
  } = useAgentJobHistory(guid || '', 10, true)

  const [isRefreshing, setIsRefreshing] = useState(false)

  // Update header stats
  useEffect(() => {
    if (agent) {
      setStats([
        { label: 'Jobs Completed', value: agent.total_jobs_completed },
        { label: 'Jobs Failed', value: agent.total_jobs_failed },
      ])
    }
    return () => setStats([])
  }, [agent, setStats])

  // Handle manual refresh
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  // Handle pagination
  const handleNextPage = () => {
    const newOffset = jobsOffset + jobsLimit
    if (newOffset < totalJobs) {
      fetchPage(newOffset)
    }
  }

  const handlePrevPage = () => {
    const newOffset = Math.max(0, jobsOffset - jobsLimit)
    fetchPage(newOffset)
  }

  // Loading state
  if (loading && !agent) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded bg-muted animate-pulse" />
          <div className="h-8 w-64 rounded bg-muted animate-pulse" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="h-32 rounded bg-muted animate-pulse" />
          <div className="h-32 rounded bg-muted animate-pulse" />
          <div className="h-32 rounded bg-muted animate-pulse" />
        </div>
        <div className="h-64 rounded bg-muted animate-pulse" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/agents')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  // Not found state
  if (!agent) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/agents')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agents
        </Button>
        <Alert>
          <AlertDescription>Agent not found</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4 min-w-0">
          <Button variant="ghost" size="icon" className="shrink-0" onClick={() => navigate('/agents')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <h1 className="text-2xl font-bold truncate">{agent.name}</h1>
              <AgentStatusBadge status={agent.status} />
              {wsConnected && (
                <Badge variant="outline" className="text-xs">
                  <Activity className="mr-1 h-3 w-3" />
                  Live
                </Badge>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <GuidBadge guid={agent.guid} />
              <span className="text-sm text-muted-foreground hidden sm:inline">•</span>
              <span className="text-sm text-muted-foreground truncate">{agent.hostname}</span>
            </div>
          </div>
        </div>
        <Button variant="outline" className="shrink-0 self-start sm:self-auto" onClick={handleRefresh} disabled={isRefreshing}>
          {isRefreshing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {/* Error Message */}
      {agent.error_message && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{agent.error_message}</AlertDescription>
        </Alert>
      )}

      {/* System Metrics */}
      <div>
        <h2 className="text-lg font-semibold mb-4">System Metrics</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard
            title="CPU Usage"
            icon={Cpu}
            value={agent.metrics?.cpu_percent?.toFixed(1) ?? null}
            unit="%"
            percentage={agent.metrics?.cpu_percent}
          />
          <MetricCard
            title="Memory Usage"
            icon={Server}
            value={agent.metrics?.memory_percent?.toFixed(1) ?? null}
            unit="%"
            percentage={agent.metrics?.memory_percent}
          />
          <MetricCard
            title="Disk Free"
            icon={HardDrive}
            value={agent.metrics?.disk_free_gb?.toFixed(1) ?? null}
            unit="GB"
          />
        </div>
      </div>

      {/* Job Statistics */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Job Statistics</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            title="Jobs Completed"
            icon={CheckCircle}
            value={agent.total_jobs_completed}
            iconColor="text-green-500"
          />
          <StatCard
            title="Jobs Failed"
            icon={XCircle}
            value={agent.total_jobs_failed}
            iconColor="text-red-500"
          />
          <StatCard
            title="Bound Collections"
            icon={FolderOpen}
            value={agent.bound_collections_count}
          />
        </div>
      </div>

      {/* Agent Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            Agent Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Operating System</dt>
              <dd className="text-sm mt-1">{agent.os_info}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Agent Version</dt>
              <dd className="text-sm mt-1 truncate" title={agent.version}>{agent.version}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Last Heartbeat</dt>
              <dd className="text-sm mt-1">
                {agent.last_heartbeat ? (
                  <span title={formatDateTime(agent.last_heartbeat)}>
                    {formatRelativeTime(agent.last_heartbeat)}
                  </span>
                ) : (
                  'Never'
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Registered</dt>
              <dd className="text-sm mt-1">{formatDateTime(agent.created_at)}</dd>
            </div>
          </dl>

          <hr className="my-4 border-border" />

          <div>
            <h4 className="text-sm font-medium text-muted-foreground mb-2">Capabilities</h4>
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.length > 0 ? (
                agent.capabilities.map((cap) => (
                  <Badge key={cap} variant="secondary">
                    {cap}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No capabilities reported</span>
              )}
            </div>
          </div>

          {agent.authorized_roots.length > 0 && (
            <>
              <hr className="my-4 border-border" />
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Authorized Roots</h4>
                <ul className="space-y-1">
                  {agent.authorized_roots.map((root) => (
                    <li key={root} className="text-sm font-mono text-muted-foreground truncate" title={root}>
                      {root}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          <AuditTrailSection audit={agent.audit} />
        </CardContent>
      </Card>

      {/* Current Job */}
      {agent.current_job_guid && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 animate-pulse text-green-500" />
              Currently Running
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm text-muted-foreground shrink-0">Job:</span>
              <Link
                to={`/jobs?guid=${agent.current_job_guid}`}
                className="text-sm font-mono text-primary hover:underline truncate"
              >
                {agent.current_job_guid}
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Recent Jobs
          </CardTitle>
          <CardDescription>
            Job history for this agent ({totalJobs} total)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {jobsLoading && jobs.length === 0 ? (
            <div className="space-y-2">
              <div className="h-10 w-full rounded bg-muted animate-pulse" />
              <div className="h-10 w-full rounded bg-muted animate-pulse" />
              <div className="h-10 w-full rounded bg-muted animate-pulse" />
            </div>
          ) : (
            <>
              <ResponsiveTable<AgentJobHistoryItem>
                data={jobs}
                columns={jobColumns}
                keyField="guid"
                emptyState={
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No jobs have been executed by this agent
                  </p>
                }
              />

              {/* Pagination */}
              {totalJobs > jobsLimit && (
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Showing {jobsOffset + 1} - {Math.min(jobsOffset + jobsLimit, totalJobs)} of{' '}
                    {totalJobs}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePrevPage}
                      disabled={jobsOffset === 0 || jobsLoading}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleNextPage}
                      disabled={jobsOffset + jobsLimit >= totalJobs || jobsLoading}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
