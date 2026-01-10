/**
 * Analytics Page
 *
 * Consolidated view for analysis trends, reports, and tool runs.
 * Three tabs:
 * - Trends: Summary view with trend charts across all collections
 * - Reports: Detailed analysis results with filtering and detail view
 * - Runs: Job execution monitoring and tool launching
 */

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Play,
  RefreshCw,
  TrendingUp,
  FileText,
  Clock,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useTools, useQueueStatus } from '@/hooks/useTools'
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

  // Dialog state
  const [runDialogOpen, setRunDialogOpen] = useState(false)

  // Result detail state - uses guid (e.g., res_xxx)
  const [selectedResultId, setSelectedResultId] = useState<string | null>(
    urlResultId || null
  )
  const [detailOpen, setDetailOpen] = useState(!!urlResultId)

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

  // Queue status for stats (defined first so onJobComplete can use refetch)
  const { queueStatus, refetch: refetchQueueStatus } = useQueueStatus()

  // Result stats (defined first so onJobComplete can use refetch)
  const { stats: resultStats, refetch: refetchResultStats } = useResultStats()

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
    fetchJobs,
    runTool,
    cancelJob
  } = useTools({ useWebSocket: true, onJobComplete: handleJobComplete })

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
    collectionId: selectedCollectionIds.length === 1 ? selectedCollectionIds[0] : undefined
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
        fetchJobs()
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

  // View result from job card (receives result_guid from job)
  const handleViewResult = (resultGuid: string) => {
    setSelectedResultId(resultGuid)
    setDetailOpen(true)
    setSearchParams({ tab: 'reports', id: resultGuid })
    setActiveTab('reports')
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

  // Group jobs by status
  const groupedJobs = {
    active: jobs.filter((j) => j.status === 'queued' || j.status === 'running'),
    completed: jobs.filter((j) => j.status === 'completed'),
    failed: jobs.filter((j) => j.status === 'failed' || j.status === 'cancelled')
  }

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
            onViewResult={handleViewResult}
          />
        ))}
      </div>
    )
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
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

      {/* Error Alert */}
      {currentError && (
        <Alert variant="destructive">
          <AlertDescription>{currentError}</AlertDescription>
        </Alert>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
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
        </TabsList>

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
          <Tabs defaultValue="active" className="w-full">
            <TabsList>
              <TabsTrigger value="active" className="gap-2">
                <Clock className="h-4 w-4" />
                Active ({groupedJobs.active.length})
              </TabsTrigger>
              <TabsTrigger value="completed" className="gap-2">
                <CheckCircle className="h-4 w-4" />
                Completed ({groupedJobs.completed.length})
              </TabsTrigger>
              <TabsTrigger value="failed" className="gap-2">
                <XCircle className="h-4 w-4" />
                Failed ({groupedJobs.failed.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="active" className="mt-6">
              {jobsLoading && jobs.length === 0 ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                renderJobGrid(
                  groupedJobs.active,
                  'No active jobs. Click "Run Tool" to start an analysis.'
                )
              )}
            </TabsContent>

            <TabsContent value="completed" className="mt-6">
              {renderJobGrid(groupedJobs.completed, 'No completed jobs yet.')}
            </TabsContent>

            <TabsContent value="failed" className="mt-6">
              {renderJobGrid(groupedJobs.failed, 'No failed jobs.')}
            </TabsContent>
          </Tabs>
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
