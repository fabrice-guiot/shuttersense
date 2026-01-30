/**
 * Analytics Page
 *
 * Consolidated view for analysis trends, reports, and tool runs.
 * Three tabs:
 * - Trends: Summary view with trend charts across all collections
 * - Reports: Detailed analysis results with filtering and detail view
 * - Runs: Job execution monitoring and tool launching
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import {
  Play,
  RefreshCw,
  TrendingUp,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  CalendarClock,
  AlertTriangle,
  HardDrive
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ResponsiveTabsList, type TabOption } from '@/components/ui/responsive-tabs-list'
import { useTools, useQueueStatus } from '@/hooks/useTools'
import { useAgentPoolStatus } from '@/hooks/useAgentPoolStatus'
import { useResults, useResult, useResultStats, useReportDownload } from '@/hooks/useResults'
import {
  usePhotoStatsTrends,
  usePhotoPairingTrends,
  usePipelineValidationTrends,
  useDisplayGraphTrends,
  useTrendSummary
} from '@/hooks/useTrends'
import { useCollections } from '@/hooks/useCollections'
import { usePipelines } from '@/hooks/usePipelines'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { RunToolDialog } from '@/components/tools/RunToolDialog'
import { JobProgressCard } from '@/components/tools/JobProgressCard'
import { ResultsTable } from '@/components/results/ResultsTable'
import { ResultDetailPanel } from '@/components/results/ResultDetailPanel'
import {
  PhotoStatsTrend,
  PhotoPairingTrend,
  PipelineValidationTrend,
  DisplayGraphTrend,
  DateRangeFilter,
  CollectionCompare,
  PipelineFilter,
  TrendSummaryCard
} from '@/components/trends'
import { ReportStorageTab, type ReportStorageTabRef } from '@/components/analytics/ReportStorageTab'
import { getDateRangeFromPreset } from '@/contracts/api/trends-api'
import type { ToolRunRequest, Job } from '@/contracts/api/tools-api'
import type { AnalysisResultSummary, ResultListQueryParams } from '@/contracts/api/results-api'

export default function AnalyticsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Get tab and result ID from URL
  const urlTab = searchParams.get('tab') || 'trends'
  const urlResultId = searchParams.get('id')
  const [activeTab, setActiveTab] = useState(urlTab)

  // Runs sub-tab state for per-status pagination
  const [runsSubTab, setRunsSubTab] = useState<'upcoming' | 'active' | 'completed' | 'failed'>('active')
  const [jobsPage, setJobsPage] = useState(1)
  const jobsPerPage = 20

  // Dialog state
  const [runDialogOpen, setRunDialogOpen] = useState(false)

  // Result detail state - uses guid (e.g., res_xxx)
  const [selectedResultId, setSelectedResultId] = useState<string | null>(
    urlResultId || null
  )
  const [detailOpen, setDetailOpen] = useState(!!urlResultId)

  // Ref for storage tab
  const storageTabRef = useRef<ReportStorageTabRef>(null)

  // Trends filter state
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<number[]>([])
  const [selectedPipelineGuid, setSelectedPipelineGuid] = useState<string | null>(null)
  const [selectedPipelineVersion, setSelectedPipelineVersion] = useState<number | null>(null)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  // Initialize date range to last 30 days
  useEffect(() => {
    const { from_date, to_date } = getDateRangeFromPreset('last_30_days')
    setFromDate(from_date)
    setToDate(to_date)
  }, [])

  // ============================================================================
  // Data Hooks
  // ============================================================================

  // Queue status for stats (defined first so callbacks can use refetch)
  const { queueStatus, refetch: refetchQueueStatus } = useQueueStatus()

  // Agent pool status for warning banner
  const { poolStatus } = useAgentPoolStatus()
  const noAgentsAvailable = poolStatus?.online_count === 0

  // Result stats (defined first so callbacks can use refetch)
  const { stats: resultStats, refetch: refetchResultStats } = useResultStats()

  // Callback when a job starts - refresh queue stats (queued -> running)
  const handleJobStart = useCallback(() => {
    refetchQueueStatus()
  }, [refetchQueueStatus])

  // Callback when a job completes - refresh stats
  const handleJobComplete = useCallback(() => {
    refetchQueueStatus()
    refetchResultStats()
  }, [refetchQueueStatus, refetchResultStats])

  // Tools/Jobs with WebSocket for real-time updates
  const {
    jobs,
    loading: jobsLoading,
    error: jobsError,
    total: jobsTotal,
    fetchJobs,
    runTool,
    cancelJob,
    retryJob
  } = useTools({ autoFetch: false, useWebSocket: true, onJobStart: handleJobStart, onJobComplete: handleJobComplete })

  // Results data
  const {
    results,
    total,
    loading: resultsLoading,
    error: resultsError,
    filters,
    setFilters,
    page,
    setPage,
    limit,
    setLimit,
    deleteResult,
    refetch: refetchResults
  } = useResults()

  // Single result for detail view
  const { result: selectedResult } = useResult(detailOpen ? selectedResultId : null)

  // Report download
  const { downloadReport } = useReportDownload()

  // Collections for filtering
  const { collections, loading: collectionsLoading } = useCollections({ autoFetch: true })

  // Pipelines for filtering and run dialog
  const { pipelines } = usePipelines({ autoFetch: true })

  // Trend data hooks
  const photoStatsTrends = usePhotoStatsTrends()
  const photoPairingTrends = usePhotoPairingTrends()
  const pipelineValidationTrends = usePipelineValidationTrends()
  const displayGraphTrends = useDisplayGraphTrends()
  const {
    summary: trendSummary,
    loading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary
  } = useTrendSummary({
    // selectedCollectionIds actually contains GUIDs (strings) cast as numbers
    collectionGuid: selectedCollectionIds.length === 1
      ? (selectedCollectionIds[0] as unknown as string)
      : undefined
  })

  // Header stats context
  const { setStats } = useHeaderStats()

  // ============================================================================
  // Effects
  // ============================================================================

  // Combined header stats: Results stats + Queued/Running from queue status
  useEffect(() => {
    const statsArray: Array<{ label: string; value: string | number }> = []

    // Add Queued and Running from queue status (real-time)
    if (queueStatus) {
      statsArray.push({ label: 'Queued', value: queueStatus.queued_count })
      statsArray.push({ label: 'Running', value: queueStatus.running_count })
    }

    // Add stats from results
    if (resultStats) {
      statsArray.push({ label: 'Completed', value: resultStats.completed_count })
      statsArray.push({ label: 'Failed', value: resultStats.failed_count })
    }

    setStats(statsArray)
    return () => setStats([])
  }, [queueStatus, resultStats, setStats])

  // Handle URL parameter for result ID (navigating from jobs)
  useEffect(() => {
    if (urlResultId) {
      setSelectedResultId(urlResultId)
      setDetailOpen(true)
      // Switch to reports tab when viewing a result
      if (activeTab !== 'reports') {
        setActiveTab('reports')
      }
    }
  }, [urlResultId])

  // Fetch trends when filters change (only when on trends tab)
  useEffect(() => {
    if (activeTab === 'trends') {
      const trendFilters = {
        collection_ids:
          selectedCollectionIds.length > 0 ? selectedCollectionIds.join(',') : undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined
      }

      photoStatsTrends.setFilters(trendFilters)
      photoPairingTrends.setFilters(trendFilters)
      pipelineValidationTrends.setFilters({
        ...trendFilters,
        pipeline_id: selectedPipelineGuid as unknown as number ?? undefined,
        pipeline_version: selectedPipelineVersion ?? undefined
      })
      displayGraphTrends.setFilters({
        pipeline_ids: selectedPipelineGuid ?? undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined
      })
      refetchSummary()
    }
  }, [
    activeTab,
    selectedCollectionIds,
    selectedPipelineGuid,
    selectedPipelineVersion,
    fromDate,
    toDate
  ])

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev)
      if (value === 'trends') {
        newParams.delete('tab')
      } else {
        newParams.set('tab', value)
      }
      // Keep result id if present
      if (urlResultId) {
        newParams.set('id', urlResultId)
      }
      return newParams
    })

    // Refresh data when switching to reports tab (ensures new results are visible)
    if (value === 'reports') {
      refetchResults()
    }
  }

  // Refresh only the selected tab
  const handleRefresh = () => {
    // Always refresh stats
    refetchQueueStatus()
    refetchResultStats()

    switch (activeTab) {
      case 'trends':
        photoStatsTrends.refetch()
        photoPairingTrends.refetch()
        pipelineValidationTrends.refetch()
        displayGraphTrends.refetch()
        refetchSummary()
        break
      case 'reports':
        refetchResults()
        break
      case 'runs':
        fetchJobsForSubTab()
        break
      case 'storage':
        storageTabRef.current?.refetch()
        break
    }
  }

  // Run tool handler
  const handleRunTool = async (request: ToolRunRequest) => {
    await runTool(request)
    refetchQueueStatus()
  }

  // Cancel job handler
  const handleCancelJob = async (jobId: string) => {
    await cancelJob(jobId)
    refetchQueueStatus()
  }

  // Retry job handler
  const handleRetryJob = async (jobId: string) => {
    await retryJob(jobId)
    refetchQueueStatus()
  }

  // Map runs sub-tab to status filter(s)
  const getStatusesForSubTab = (subTab: 'upcoming' | 'active' | 'completed' | 'failed'): ('scheduled' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled')[] => {
    switch (subTab) {
      case 'upcoming':
        return ['scheduled']
      case 'active':
        return ['queued', 'running']
      case 'completed':
        return ['completed']
      case 'failed':
        return ['failed', 'cancelled']
    }
  }

  // Fetch jobs for current runs sub-tab with pagination
  const fetchJobsForSubTab = useCallback(() => {
    const statuses = getStatusesForSubTab(runsSubTab)
    const offset = (jobsPage - 1) * jobsPerPage
    fetchJobs({ status: statuses, limit: jobsPerPage, offset })
  }, [runsSubTab, jobsPage, jobsPerPage, fetchJobs])

  // Fetch jobs when runs sub-tab or page changes
  useEffect(() => {
    if (activeTab === 'runs') {
      fetchJobsForSubTab()
    }
  }, [activeTab, runsSubTab, jobsPage, fetchJobsForSubTab])

  // Handle runs sub-tab change - reset to page 1
  const handleRunsSubTabChange = (value: string) => {
    setRunsSubTab(value as 'upcoming' | 'active' | 'completed' | 'failed')
    setJobsPage(1)
  }

  // View result from job card (receives result_guid from job)
  const handleViewResult = (resultGuid: string) => {
    setSelectedResultId(resultGuid)
    setDetailOpen(true)
    setSearchParams({ tab: 'reports', id: resultGuid })
    setActiveTab('reports')
    refetchResults() // Refresh to ensure the new result appears in table
  }

  // View result from table
  const handleViewResultFromTable = (result: AnalysisResultSummary) => {
    setSelectedResultId(result.guid)
    setDetailOpen(true)
    setSearchParams({ tab: 'reports', id: result.guid })
  }

  // Close detail panel
  const handleCloseDetail = (open: boolean) => {
    setDetailOpen(open)
    if (!open) {
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev)
        newParams.delete('id')
        return newParams
      })
    }
  }

  // Delete result
  const handleDelete = async (result: AnalysisResultSummary) => {
    await deleteResult(result.guid)
    refetchResultStats()
  }

  // Download report
  const handleDownloadReport = async (result: AnalysisResultSummary) => {
    await downloadReport(result.guid)
  }

  // Results filter change
  const handleFiltersChange = (newFilters: ResultListQueryParams) => {
    setFilters(newFilters)
  }

  // Trends date change
  const handleDateChange = (from: string, to: string) => {
    setFromDate(from)
    setToDate(to)
  }

  // ============================================================================
  // Derived State
  // ============================================================================

  // Tab options for ResponsiveTabsList
  const mainTabOptions: TabOption[] = [
    { value: 'trends', label: 'Trends', icon: TrendingUp },
    { value: 'reports', label: 'Reports', icon: FileText },
    { value: 'runs', label: 'Runs', icon: Clock },
    { value: 'storage', label: 'Storage', icon: HardDrive },
  ]

  const runsSubTabOptions: TabOption[] = [
    {
      value: 'upcoming',
      label: 'Upcoming',
      icon: CalendarClock,
      badge: queueStatus && queueStatus.scheduled_count > 0 ? (
        <span className="text-xs">({queueStatus.scheduled_count})</span>
      ) : undefined,
    },
    {
      value: 'active',
      label: 'Active',
      icon: Clock,
      badge: queueStatus && (queueStatus.queued_count + queueStatus.running_count) > 0 ? (
        <span className="text-xs">({queueStatus.queued_count + queueStatus.running_count})</span>
      ) : undefined,
    },
    {
      value: 'completed',
      label: 'Completed',
      icon: CheckCircle,
      badge: queueStatus && queueStatus.completed_count > 0 ? (
        <span className="text-xs">({queueStatus.completed_count})</span>
      ) : undefined,
    },
    {
      value: 'failed',
      label: 'Failed',
      icon: XCircle,
      badge: queueStatus && (queueStatus.failed_count + queueStatus.cancelled_count) > 0 ? (
        <span className="text-xs">({queueStatus.failed_count + queueStatus.cancelled_count})</span>
      ) : undefined,
    },
  ]

  // Loading state based on active tab
  const isLoading =
    activeTab === 'trends'
      ? photoStatsTrends.loading
      : activeTab === 'reports'
        ? resultsLoading
        : jobsLoading

  // Error state based on active tab
  const currentError =
    activeTab === 'trends'
      ? photoStatsTrends.error
      : activeTab === 'reports'
        ? resultsError
        : jobsError

  // ============================================================================
  // Render Helpers
  // ============================================================================

  const renderJobGrid = (jobList: Job[], emptyMessage: string) => {
    if (jobList.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Clock className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-muted-foreground">{emptyMessage}</p>
        </div>
      )
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {jobList.map((job) => (
          <JobProgressCard
            key={job.id}
            job={job}
            onCancel={handleCancelJob}
            onRetry={handleRetryJob}
            onViewResult={handleViewResult}
          />
        ))}
      </div>
    )
  }

  const renderJobsPagination = () => {
    const totalPages = Math.ceil(jobsTotal / jobsPerPage)
    if (totalPages <= 1) return null

    return (
      <div className="flex items-center justify-center gap-2 mt-6">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setJobsPage((p) => Math.max(1, p - 1))}
          disabled={jobsPage === 1 || jobsLoading}
        >
          Previous
        </Button>
        <span className="text-sm text-muted-foreground">
          Page {jobsPage} of {totalPages} ({jobsTotal} total)
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setJobsPage((p) => Math.min(totalPages, p + 1))}
          disabled={jobsPage === totalPages || jobsLoading}
        >
          Next
        </Button>
      </div>
    )
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="flex flex-col gap-6">
      {/* Error Alert */}
      {currentError && (
        <Alert variant="destructive">
          <AlertDescription>{currentError}</AlertDescription>
        </Alert>
      )}

      {/* No Agents Warning (Issue #90 - T215) */}
      {noAgentsAvailable && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>No agents available</AlertTitle>
          <AlertDescription>
            Analysis jobs require at least one agent to process. Jobs will remain queued until an agent becomes available.{' '}
            <Link to="/agents" className="underline hover:no-underline">
              Manage agents
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Tabs with Action Buttons (Issue #67 - Single Title Pattern) */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <ResponsiveTabsList
            tabs={mainTabOptions}
            value={activeTab}
            onValueChange={handleTabChange}
          >
            <TabsTrigger value="trends" className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Trends
            </TabsTrigger>
            <TabsTrigger value="reports" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Reports
            </TabsTrigger>
            <TabsTrigger value="runs" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Runs
            </TabsTrigger>
            <TabsTrigger value="storage" className="flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Storage
            </TabsTrigger>
          </ResponsiveTabsList>
          <div className="flex gap-2">
            <Button variant="outline" size="icon" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={() => setRunDialogOpen(true)} className="gap-2">
              <Play className="h-4 w-4" />
              Run Tool
            </Button>
          </div>
        </div>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-6">
          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <DateRangeFilter
              fromDate={fromDate}
              toDate={toDate}
              onDateChange={handleDateChange}
            />
            <PipelineFilter
              pipelines={pipelines}
              selectedPipelineGuid={selectedPipelineGuid}
              selectedPipelineVersion={selectedPipelineVersion}
              onPipelineChange={setSelectedPipelineGuid}
              onVersionChange={setSelectedPipelineVersion}
            />
            <div className="md:col-span-2">
              <CollectionCompare
                collections={collections
                  .filter((c) => c.is_accessible)
                  .map((c) => ({ id: c.guid as unknown as number, name: c.name }))}
                selectedIds={selectedCollectionIds}
                onSelectionChange={setSelectedCollectionIds}
                maxSelections={5}
              />
            </div>
          </div>

          {/* Trend Summary */}
          <TrendSummaryCard
            summary={trendSummary}
            loading={summaryLoading}
            error={summaryError}
          />

          {/* Trend Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PhotoStatsTrend
              data={photoStatsTrends.data}
              loading={photoStatsTrends.loading}
              error={photoStatsTrends.error}
            />
            <PhotoPairingTrend
              data={photoPairingTrends.data}
              loading={photoPairingTrends.loading}
              error={photoPairingTrends.error}
            />
          </div>

          <PipelineValidationTrend
            data={pipelineValidationTrends.data}
            loading={pipelineValidationTrends.loading}
            error={pipelineValidationTrends.error}
          />

          <DisplayGraphTrend
            data={displayGraphTrends.data}
            loading={displayGraphTrends.loading}
            error={displayGraphTrends.error}
          />
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports">
          <ResultsTable
            results={results}
            total={total}
            page={page}
            limit={limit}
            loading={resultsLoading}
            onPageChange={setPage}
            onLimitChange={setLimit}
            onFiltersChange={handleFiltersChange}
            onView={handleViewResultFromTable}
            onDelete={handleDelete}
            onDownloadReport={handleDownloadReport}
          />
        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs">
          <Tabs value={runsSubTab} onValueChange={handleRunsSubTabChange} className="w-full">
            <ResponsiveTabsList
              tabs={runsSubTabOptions}
              value={runsSubTab}
              onValueChange={handleRunsSubTabChange}
            >
              <TabsTrigger value="upcoming" className="gap-2">
                <CalendarClock className="h-4 w-4" />
                Upcoming
                {queueStatus && queueStatus.scheduled_count > 0 && (
                  <span className="ml-1 text-xs">({queueStatus.scheduled_count})</span>
                )}
              </TabsTrigger>
              <TabsTrigger value="active" className="gap-2">
                <Clock className="h-4 w-4" />
                Active
                {queueStatus && (queueStatus.queued_count + queueStatus.running_count) > 0 && (
                  <span className="ml-1 text-xs">({queueStatus.queued_count + queueStatus.running_count})</span>
                )}
              </TabsTrigger>
              <TabsTrigger value="completed" className="gap-2">
                <CheckCircle className="h-4 w-4" />
                Completed
                {queueStatus && queueStatus.completed_count > 0 && (
                  <span className="ml-1 text-xs">({queueStatus.completed_count})</span>
                )}
              </TabsTrigger>
              <TabsTrigger value="failed" className="gap-2">
                <XCircle className="h-4 w-4" />
                Failed
                {queueStatus && (queueStatus.failed_count + queueStatus.cancelled_count) > 0 && (
                  <span className="ml-1 text-xs">({queueStatus.failed_count + queueStatus.cancelled_count})</span>
                )}
              </TabsTrigger>
            </ResponsiveTabsList>

            <TabsContent value="upcoming" className="mt-6">
              {jobsLoading && jobs.length === 0 ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <>
                  {renderJobGrid(
                    jobs,
                    'No scheduled jobs. Jobs are automatically scheduled after analysis based on collection TTL settings.'
                  )}
                  {renderJobsPagination()}
                </>
              )}
            </TabsContent>

            <TabsContent value="active" className="mt-6">
              {jobsLoading && jobs.length === 0 ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <>
                  {renderJobGrid(
                    jobs,
                    'No active jobs. Click "Run Tool" to start an analysis.'
                  )}
                  {renderJobsPagination()}
                </>
              )}
            </TabsContent>

            <TabsContent value="completed" className="mt-6">
              {jobsLoading && jobs.length === 0 ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <>
                  {renderJobGrid(jobs, 'No completed jobs yet.')}
                  {renderJobsPagination()}
                </>
              )}
            </TabsContent>

            <TabsContent value="failed" className="mt-6">
              {jobsLoading && jobs.length === 0 ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <>
                  {renderJobGrid(jobs, 'No failed jobs.')}
                  {renderJobsPagination()}
                </>
              )}
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* Storage Tab */}
        <TabsContent value="storage">
          <ReportStorageTab ref={storageTabRef} />
        </TabsContent>
      </Tabs>

      {/* Run Tool Dialog */}
      <RunToolDialog
        open={runDialogOpen}
        onOpenChange={setRunDialogOpen}
        collections={collections}
        pipelines={pipelines}
        onRunTool={handleRunTool}
      />

      {/* Result Detail Panel */}
      <ResultDetailPanel
        result={selectedResult}
        open={detailOpen}
        onOpenChange={handleCloseDetail}
        onDownloadReport={(id) => downloadReport(id)}
      />
    </div>
  )
}
