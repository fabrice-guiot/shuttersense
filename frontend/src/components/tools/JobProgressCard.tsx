/**
 * Job Progress Card Component
 *
 * Displays job status and progress with real-time updates
 */

import { useEffect } from 'react'
import {
  Clock,
  Play,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { useJobProgress } from '@/hooks/useTools'
import type { Job, JobStatus, ProgressData } from '@/contracts/api/tools-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Types
// ============================================================================

interface JobProgressCardProps {
  job: Job
  onCancel?: (jobId: string) => void
  onViewResult?: (resultGuid: string) => void
  className?: string
}

// Status display configuration
const STATUS_CONFIG: Record<
  JobStatus,
  { icon: typeof Clock; color: string; label: string; badgeVariant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  queued: {
    icon: Clock,
    color: 'text-yellow-500',
    label: 'Queued',
    badgeVariant: 'secondary'
  },
  running: {
    icon: Loader2,
    color: 'text-blue-500',
    label: 'Running',
    badgeVariant: 'default'
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    label: 'Completed',
    badgeVariant: 'outline'
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    label: 'Failed',
    badgeVariant: 'destructive'
  },
  cancelled: {
    icon: AlertCircle,
    color: 'text-gray-500',
    label: 'Cancelled',
    badgeVariant: 'secondary'
  }
}

// Tool display names
const TOOL_LABELS: Record<string, string> = {
  photostats: 'PhotoStats',
  photo_pairing: 'Photo Pairing',
  pipeline_validation: 'Pipeline Validation'
}

// ============================================================================
// Component
// ============================================================================

export function JobProgressCard({
  job,
  onCancel,
  onViewResult,
  className
}: JobProgressCardProps) {
  // WebSocket progress for running jobs
  const { progress, status: wsStatus } = useJobProgress(
    job.status === 'running' || job.status === 'queued' ? job.id : null
  )

  // Use WebSocket status if available, otherwise use job status
  const currentStatus = wsStatus || job.status
  const currentProgress = progress || job.progress
  const config = STATUS_CONFIG[currentStatus]
  const StatusIcon = config.icon

  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return '-'
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString()
  }

  const canCancel = currentStatus === 'queued'
  const hasResult = currentStatus === 'completed' && job.result_guid !== null

  return (
    <Card className={cn('relative', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <StatusIcon
              className={cn(
                'h-5 w-5',
                config.color,
                currentStatus === 'running' && 'animate-spin'
              )}
            />
            {TOOL_LABELS[job.tool] || job.tool}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={config.badgeVariant}>{config.label}</Badge>
            {canCancel && onCancel && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => onCancel(job.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Cancel Job</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Progress bar for running jobs */}
        {currentStatus === 'running' && currentProgress && (
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground capitalize">
                {currentProgress.stage.replace('_', ' ')}
              </span>
              <span className="font-medium">{currentProgress.percentage}%</span>
            </div>
            <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${currentProgress.percentage}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{currentProgress.files_scanned} files scanned</span>
              <span>{currentProgress.issues_found} issues found</span>
            </div>
          </div>
        )}

        {/* Queue position for queued jobs */}
        {currentStatus === 'queued' && job.position !== null && (
          <div className="text-sm text-muted-foreground">
            Position in queue: <span className="font-medium">{job.position}</span>
          </div>
        )}

        {/* Error message for failed jobs */}
        {currentStatus === 'failed' && job.error_message && (
          <div className="text-sm text-destructive bg-destructive/10 p-2 rounded">
            {job.error_message}
          </div>
        )}

        {/* Job details */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">Collection:</div>
          <div className="font-medium">{job.collection_guid || 'N/A'}</div>

          <div className="text-muted-foreground">Created:</div>
          <div>{formatDate(job.created_at)}</div>

          {job.started_at && (
            <>
              <div className="text-muted-foreground">Started:</div>
              <div>{formatDate(job.started_at)}</div>
            </>
          )}

          {job.completed_at && (
            <>
              <div className="text-muted-foreground">Completed:</div>
              <div>{formatDate(job.completed_at)}</div>
            </>
          )}
        </div>

        {/* View Result button */}
        {hasResult && onViewResult && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => onViewResult(job.result_guid!)}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            View Result
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
