/**
 * Result Detail Panel Component
 *
 * Displays detailed analysis result information in a side panel or dialog
 */

import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Download,
  Clock,
  FileText,
  Camera,
  FolderOpen,
  AlertTriangle
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type {
  AnalysisResult,
  ResultStatus,
  PhotoStatsResults,
  PhotoPairingResults,
  PipelineValidationResults
} from '@/contracts/api/results-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Types
// ============================================================================

interface ResultDetailPanelProps {
  result: AnalysisResult | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownloadReport?: (resultId: number) => void
}

// Status display configuration
const STATUS_CONFIG: Record<
  ResultStatus,
  { icon: typeof CheckCircle; color: string; label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' }
> = {
  COMPLETED: {
    icon: CheckCircle,
    color: 'text-green-500',
    label: 'Completed',
    variant: 'success'
  },
  FAILED: {
    icon: XCircle,
    color: 'text-red-500',
    label: 'Failed',
    variant: 'destructive'
  },
  CANCELLED: {
    icon: AlertCircle,
    color: 'text-gray-500',
    label: 'Cancelled',
    variant: 'secondary'
  }
}

// Tool display names
const TOOL_LABELS: Record<string, string> = {
  photostats: 'PhotoStats',
  photo_pairing: 'Photo Pairing',
  pipeline_validation: 'Pipeline Validation'
}

// ============================================================================
// Sub-components for tool-specific results
// ============================================================================

function PhotoStatsResultsView({ results }: { results: PhotoStatsResults }) {
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Total Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{results.total_files}</div>
            <div className="text-sm text-muted-foreground">
              {formatSize(results.total_size)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              Orphaned Files
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {results.orphaned_images.length + results.orphaned_xmp.length}
            </div>
            <div className="text-sm text-muted-foreground">
              {results.orphaned_images.length} images, {results.orphaned_xmp.length} XMP
            </div>
          </CardContent>
        </Card>
      </div>

      {/* File counts by extension */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Files by Extension</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(results.file_counts).map(([ext, count]) => (
              <Badge key={ext} variant="secondary">
                {ext}: {count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Orphaned files (if any) */}
      {(results.orphaned_images.length > 0 || results.orphaned_xmp.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-yellow-600">
              Orphaned Files
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {results.orphaned_images.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  Orphaned Images ({results.orphaned_images.length})
                </div>
                <div className="max-h-32 overflow-y-auto text-xs font-mono bg-muted p-2 rounded">
                  {results.orphaned_images.slice(0, 10).map((file, i) => (
                    <div key={i} className="truncate">{file}</div>
                  ))}
                  {results.orphaned_images.length > 10 && (
                    <div className="text-muted-foreground">
                      ...and {results.orphaned_images.length - 10} more
                    </div>
                  )}
                </div>
              </div>
            )}
            {results.orphaned_xmp.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  Orphaned XMP Files ({results.orphaned_xmp.length})
                </div>
                <div className="max-h-32 overflow-y-auto text-xs font-mono bg-muted p-2 rounded">
                  {results.orphaned_xmp.slice(0, 10).map((file, i) => (
                    <div key={i} className="truncate">{file}</div>
                  ))}
                  {results.orphaned_xmp.length > 10 && (
                    <div className="text-muted-foreground">
                      ...and {results.orphaned_xmp.length - 10} more
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

interface CameraDisplayInfo {
  id: string
  name: string
  imageCount: number
}

function PhotoPairingResultsView({ results }: { results: PhotoPairingResults }) {
  // Defensive access with fallbacks for backward compatibility
  // Old results may have imagegroups_count instead of group_count
  const rawResults = results as unknown as Record<string, unknown>
  const groupCount = Number(results.group_count ?? rawResults.imagegroups_count ?? 0)
  const imageCount = Number(results.image_count ?? rawResults.total_images ?? 0)

  // Transform camera_usage - handles both formats:
  // Rich format: { "CAM_ID": { name: "Canon EOS R5", image_count: 10, ... } }
  // Simple format: { "CAM_ID": 10 }
  const rawCameraUsage = results.camera_usage ?? {}
  const cameras: CameraDisplayInfo[] = Object.entries(rawCameraUsage)
    .map(([camId, value]) => {
      if (typeof value === 'number') {
        return { id: camId, name: camId, imageCount: value }
      } else if (typeof value === 'object' && value !== null) {
        const info = value as { name?: string; image_count?: number }
        return {
          id: camId,
          name: info.name || camId,
          imageCount: info.image_count ?? 0
        }
      }
      return { id: camId, name: camId, imageCount: 0 }
    })
    .sort((a, b) => b.imageCount - a.imageCount)

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Image Groups
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{groupCount}</div>
            <div className="text-sm text-muted-foreground">
              {imageCount} total images
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Camera className="h-4 w-4" />
              Cameras
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {cameras.length}
            </div>
            <div className="text-sm text-muted-foreground">unique cameras</div>
          </CardContent>
        </Card>
      </div>

      {/* Camera usage */}
      {cameras.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Camera Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {cameras.map((camera) => (
                <div key={camera.id} className="flex justify-between items-center">
                  <span className="text-sm">{camera.name}</span>
                  <Badge variant="outline">{camera.imageCount} images</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function PipelineValidationResultsView({ results }: { results: PipelineValidationResults }) {
  const total =
    results.consistency_counts.CONSISTENT +
    results.consistency_counts.PARTIAL +
    results.consistency_counts.INCONSISTENT

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-600">
              Consistent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {results.consistency_counts.CONSISTENT}
            </div>
            <div className="text-sm text-muted-foreground">
              {total > 0 ? ((results.consistency_counts.CONSISTENT / total) * 100).toFixed(1) : 0}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-yellow-600">
              Partial
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {results.consistency_counts.PARTIAL}
            </div>
            <div className="text-sm text-muted-foreground">
              {total > 0 ? ((results.consistency_counts.PARTIAL / total) * 100).toFixed(1) : 0}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-600">
              Inconsistent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {results.consistency_counts.INCONSISTENT}
            </div>
            <div className="text-sm text-muted-foreground">
              {total > 0 ? ((results.consistency_counts.INCONSISTENT / total) * 100).toFixed(1) : 0}%
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function ResultDetailPanel({
  result,
  open,
  onOpenChange,
  onDownloadReport
}: ResultDetailPanelProps) {
  if (!result) return null

  const statusConfig = STATUS_CONFIG[result.status]
  const StatusIcon = statusConfig.icon

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString()
  }

  const renderToolResults = () => {
    switch (result.tool) {
      case 'photostats':
        return <PhotoStatsResultsView results={result.results as PhotoStatsResults} />
      case 'photo_pairing':
        return <PhotoPairingResultsView results={result.results as PhotoPairingResults} />
      case 'pipeline_validation':
        return (
          <PipelineValidationResultsView
            results={result.results as PipelineValidationResults}
          />
        )
      default:
        return (
          <pre className="text-xs bg-muted p-4 rounded overflow-auto max-h-64">
            {JSON.stringify(result.results, null, 2)}
          </pre>
        )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <StatusIcon className={cn('h-5 w-5', statusConfig.color)} />
            {TOOL_LABELS[result.tool] || result.tool} Analysis
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Header info */}
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
            <span className="text-sm text-muted-foreground">
              {result.collection_name}
            </span>
            {result.pipeline_name && (
              <Badge variant="outline">Pipeline: {result.pipeline_name}</Badge>
            )}
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Duration:</span>
              <span className="font-medium">{formatDuration(result.duration_seconds)}</span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Files:</span>
              <span className="font-medium">{result.files_scanned ?? '-'}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Started:</span>{' '}
              <span className="font-medium">{formatDate(result.started_at)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Completed:</span>{' '}
              <span className="font-medium">{formatDate(result.completed_at)}</span>
            </div>
          </div>

          {/* Error message if failed */}
          {result.status === 'FAILED' && result.error_message && (
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-3 rounded text-sm">
              <div className="font-medium mb-1 text-red-700 dark:text-red-400">Error</div>
              <div className="text-red-600 dark:text-red-300">{result.error_message}</div>
            </div>
          )}

          {/* Tool-specific results */}
          {result.status === 'COMPLETED' && renderToolResults()}

          {/* Download report button */}
          {result.has_report && onDownloadReport && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => onDownloadReport(result.id)}
            >
              <Download className="mr-2 h-4 w-4" />
              Download HTML Report
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
