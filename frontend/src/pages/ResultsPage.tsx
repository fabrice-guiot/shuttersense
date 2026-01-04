/**
 * Results Page
 *
 * View and manage analysis results with filtering, pagination, and detail view
 */

import { useState, useEffect } from 'react'
import { FileText, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useResults, useResult, useResultStats, useReportDownload } from '@/hooks/useResults'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { ResultsTable } from '@/components/results/ResultsTable'
import { ResultDetailPanel } from '@/components/results/ResultDetailPanel'
import type { AnalysisResultSummary, ResultListQueryParams } from '@/contracts/api/results-api'
import { useSearchParams } from 'react-router-dom'

export default function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Get result ID from URL if present
  const urlResultId = searchParams.get('id')
  const [selectedResultId, setSelectedResultId] = useState<number | null>(
    urlResultId ? parseInt(urlResultId, 10) : null
  )
  const [detailOpen, setDetailOpen] = useState(!!urlResultId)

  // Fetch results data
  const {
    results,
    total,
    loading,
    error,
    filters,
    setFilters,
    page,
    setPage,
    limit,
    setLimit,
    deleteResult,
    refetch
  } = useResults()

  // Fetch single result for detail view
  const { result: selectedResult, loading: resultLoading } = useResult(
    detailOpen ? selectedResultId : null
  )

  // Stats for header KPIs
  const { stats, refetch: refetchStats } = useResultStats()
  const { setStats } = useHeaderStats()

  // Report download
  const { downloadReport } = useReportDownload()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Results', value: stats.total_results },
        { label: 'Completed', value: stats.completed_count },
        { label: 'Failed', value: stats.failed_count },
        { label: 'Last Run', value: stats.last_run ? new Date(stats.last_run).toLocaleDateString() : '-' }
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  // Handle URL parameter for result ID
  useEffect(() => {
    if (urlResultId) {
      const id = parseInt(urlResultId, 10)
      if (!isNaN(id)) {
        setSelectedResultId(id)
        setDetailOpen(true)
      }
    }
  }, [urlResultId])

  const handleView = (result: AnalysisResultSummary) => {
    setSelectedResultId(result.id)
    setDetailOpen(true)
    setSearchParams({ id: result.id.toString() })
  }

  const handleCloseDetail = (open: boolean) => {
    setDetailOpen(open)
    if (!open) {
      setSearchParams({})
    }
  }

  const handleDelete = async (result: AnalysisResultSummary) => {
    await deleteResult(result.id)
    refetchStats()
  }

  const handleDownloadReport = async (result: AnalysisResultSummary) => {
    await downloadReport(result.id)
  }

  const handleFiltersChange = (newFilters: ResultListQueryParams) => {
    setFilters(newFilters)
  }

  const handleRefresh = () => {
    refetch()
    refetchStats()
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Analysis Results</h1>
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results Table */}
      <ResultsTable
        results={results}
        total={total}
        page={page}
        limit={limit}
        loading={loading}
        onPageChange={setPage}
        onLimitChange={setLimit}
        onFiltersChange={handleFiltersChange}
        onView={handleView}
        onDelete={handleDelete}
        onDownloadReport={handleDownloadReport}
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
