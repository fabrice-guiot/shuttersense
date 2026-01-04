/**
 * Tools Page
 *
 * Execute analysis tools on collections and monitor job progress
 */

import { useState, useEffect } from 'react'
import { Play, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useTools, useQueueStatus } from '@/hooks/useTools'
import { useCollections } from '@/hooks/useCollections'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { RunToolDialog } from '@/components/tools/RunToolDialog'
import { JobProgressCard } from '@/components/tools/JobProgressCard'
import type { ToolRunRequest, Job, JobStatus } from '@/contracts/api/tools-api'
import { useNavigate } from 'react-router-dom'

export default function ToolsPage() {
  const navigate = useNavigate()

  // Fetch tools/jobs data
  const {
    jobs,
    loading,
    error,
    fetchJobs,
    runTool,
    cancelJob
  } = useTools({ pollInterval: 5000 }) // Poll every 5 seconds

  // Fetch collections for the run tool dialog
  const { collections, loading: collectionsLoading } = useCollections()

  // Queue status for header KPIs
  const { queueStatus, refetch: refetchQueueStatus } = useQueueStatus()
  const { setStats } = useHeaderStats()

  // Dialog state
  const [runDialogOpen, setRunDialogOpen] = useState(false)

  // Update header stats when queue status changes
  useEffect(() => {
    if (queueStatus) {
      setStats([
        { label: 'Queued', value: queueStatus.queued_count },
        { label: 'Running', value: queueStatus.running_count },
        { label: 'Completed', value: queueStatus.completed_count },
        { label: 'Failed', value: queueStatus.failed_count }
      ])
    }
    return () => setStats([])
  }, [queueStatus, setStats])

  // Group jobs by status
  const groupedJobs = {
    active: jobs.filter((j) => j.status === 'queued' || j.status === 'running'),
    completed: jobs.filter((j) => j.status === 'completed'),
    failed: jobs.filter((j) => j.status === 'failed' || j.status === 'cancelled')
  }

  const handleRunTool = async (request: ToolRunRequest) => {
    await runTool(request)
    refetchQueueStatus()
  }

  const handleCancelJob = async (jobId: string) => {
    await cancelJob(jobId)
    refetchQueueStatus()
  }

  const handleViewResult = (resultId: number) => {
    navigate(`/results?id=${resultId}`)
  }

  const handleRefresh = () => {
    fetchJobs()
    refetchQueueStatus()
  }

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

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Analysis Tools</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setRunDialogOpen(true)} className="gap-2">
            <Play className="h-4 w-4" />
            Run Tool
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Job Tabs */}
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
          {loading && jobs.length === 0 ? (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            renderJobGrid(groupedJobs.active, 'No active jobs. Click "Run Tool" to start an analysis.')
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-6">
          {renderJobGrid(groupedJobs.completed, 'No completed jobs yet.')}
        </TabsContent>

        <TabsContent value="failed" className="mt-6">
          {renderJobGrid(groupedJobs.failed, 'No failed jobs.')}
        </TabsContent>
      </Tabs>

      {/* Run Tool Dialog */}
      <RunToolDialog
        open={runDialogOpen}
        onOpenChange={setRunDialogOpen}
        collections={collections}
        onRunTool={handleRunTool}
      />
    </div>
  )
}
