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
  PipelineValidationResults,
  DisplayGraphResults
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

  // Defensive defaults for arrays that might be undefined
  const orphanedImages = results.orphaned_images ?? []
  const orphanedXmp = results.orphaned_xmp ?? []
  const fileCounts = results.file_counts ?? {}

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
              {orphanedImages.length + orphanedXmp.length}
            </div>
            <div className="text-sm text-muted-foreground">
              {orphanedImages.length} images, {orphanedXmp.length} XMP
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
            {Object.entries(fileCounts).map(([ext, count]) => (
              <Badge key={ext} variant="secondary">
                {ext}: {count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Orphaned files (if any) */}
      {(orphanedImages.length > 0 || orphanedXmp.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-yellow-600">
              Orphaned Files
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {orphanedImages.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  Orphaned Images ({orphanedImages.length})
                </div>
                <div className="max-h-32 overflow-y-auto text-xs font-mono bg-muted p-2 rounded">
                  {orphanedImages.slice(0, 10).map((file, i) => (
                    <div key={i} className="truncate">{file}</div>
                  ))}
                  {orphanedImages.length > 10 && (
                    <div className="text-muted-foreground">
                      ...and {orphanedImages.length - 10} more
                    </div>
                  )}
                </div>
              </div>
            )}
            {orphanedXmp.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  Orphaned XMP Files ({orphanedXmp.length})
                </div>
                <div className="max-h-32 overflow-y-auto text-xs font-mono bg-muted p-2 rounded">
                  {orphanedXmp.slice(0, 10).map((file, i) => (
                    <div key={i} className="truncate">{file}</div>
                  ))}
                  {orphanedXmp.length > 10 && (
                    <div className="text-muted-foreground">
                      ...and {orphanedXmp.length - 10} more
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

// Extended interface for backward compatibility with old and new result formats
interface ExtendedPipelineValidationResults {
  // New format (v2) - with per-termination breakdown
  overall_consistency?: {
    CONSISTENT: number
    PARTIAL: number
    INCONSISTENT: number
  }
  by_termination?: Record<string, {
    CONSISTENT: number
    PARTIAL: number
    INCONSISTENT: number
  }>
  // Old format (v1) - single consistency_counts
  consistency_counts?: {
    CONSISTENT: number
    PARTIAL: number
    INCONSISTENT: number
  }
  // Legacy format fields
  consistent_count?: number
  consistent_with_warning_count?: number
  partial_count?: number
  inconsistent_count?: number
}

// Helper component to render a status card
function StatusCard({
  title,
  value,
  total,
  colorClass,
}: {
  title: string
  value: number
  total: number
  colorClass: string
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className={`text-sm font-medium ${colorClass}`}>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="text-sm text-muted-foreground">
          {total > 0 ? ((value / total) * 100).toFixed(1) : 0}%
        </div>
      </CardContent>
    </Card>
  )
}

function PipelineValidationResultsView({ results }: { results: PipelineValidationResults }) {
  // Handle all format variations
  const extResults = results as unknown as ExtendedPipelineValidationResults

  // Extract overall consistency - try new format first, then old formats
  const overallConsistent = extResults.overall_consistency?.CONSISTENT
    ?? extResults.consistency_counts?.CONSISTENT
    ?? ((extResults.consistent_count ?? 0) + (extResults.consistent_with_warning_count ?? 0))
  const overallPartial = extResults.overall_consistency?.PARTIAL
    ?? extResults.consistency_counts?.PARTIAL
    ?? (extResults.partial_count ?? 0)
  const overallInconsistent = extResults.overall_consistency?.INCONSISTENT
    ?? extResults.consistency_counts?.INCONSISTENT
    ?? (extResults.inconsistent_count ?? 0)

  const overallTotal = overallConsistent + overallPartial + overallInconsistent

  // Get per-termination breakdown if available
  const byTermination = extResults.by_termination

  return (
    <div className="space-y-6">
      {/* Overall Status Section */}
      <div>
        <h4 className="mb-3 text-sm font-semibold text-muted-foreground">
          Overall Status (worst per image)
        </h4>
        <div className="grid grid-cols-3 gap-4">
          <StatusCard
            title="Consistent"
            value={overallConsistent}
            total={overallTotal}
            colorClass="text-green-600"
          />
          <StatusCard
            title="Partial"
            value={overallPartial}
            total={overallTotal}
            colorClass="text-yellow-600"
          />
          <StatusCard
            title="Inconsistent"
            value={overallInconsistent}
            total={overallTotal}
            colorClass="text-red-600"
          />
        </div>
      </div>

      {/* Per-Termination Breakdown */}
      {byTermination && Object.keys(byTermination).length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-muted-foreground">
            By Termination Type
          </h4>
          <div className="space-y-4">
            {Object.entries(byTermination)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([termType, counts]) => {
                const termTotal = counts.CONSISTENT + counts.PARTIAL + counts.INCONSISTENT
                return (
                  <div key={termType}>
                    <h5 className="mb-2 text-sm font-medium">{termType}</h5>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-md border p-3">
                        <div className="text-xs text-green-600">Consistent</div>
                        <div className="text-lg font-semibold">{counts.CONSISTENT}</div>
                        <div className="text-xs text-muted-foreground">
                          {termTotal > 0 ? ((counts.CONSISTENT / termTotal) * 100).toFixed(1) : 0}%
                        </div>
                      </div>
                      <div className="rounded-md border p-3">
                        <div className="text-xs text-yellow-600">Partial</div>
                        <div className="text-lg font-semibold">{counts.PARTIAL}</div>
                        <div className="text-xs text-muted-foreground">
                          {termTotal > 0 ? ((counts.PARTIAL / termTotal) * 100).toFixed(1) : 0}%
                        </div>
                      </div>
                      <div className="rounded-md border p-3">
                        <div className="text-xs text-red-600">Inconsistent</div>
                        <div className="text-lg font-semibold">{counts.INCONSISTENT}</div>
                        <div className="text-xs text-muted-foreground">
                          {termTotal > 0 ? ((counts.INCONSISTENT / termTotal) * 100).toFixed(1) : 0}%
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}
    </div>
  )
}

function DisplayGraphResultsView({ results }: { results: DisplayGraphResults & { _truncated?: Record<string, number> } }) {
  const truncatedInfo = results._truncated?.paths
  const displayedPaths = results.paths?.length ?? 0
  const nonTruncatedByTermination = results.non_truncated_by_termination ?? {}
  const terminationTypes = Object.keys(nonTruncatedByTermination).sort()

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Paths</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{results.total_paths}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Non-Truncated Paths</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{results.non_truncated_paths ?? 0}</div>
            <div className="text-sm text-muted-foreground">
              {results.total_paths > 0
                ? (((results.non_truncated_paths ?? 0) / results.total_paths) * 100).toFixed(1)
                : 0}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Version</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">v{results.pipeline_version}</div>
          </CardContent>
        </Card>
      </div>

      {/* Non-truncated paths by termination type */}
      {terminationTypes.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Paths by Termination Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {terminationTypes.map((termType) => (
                <div key={termType} className="bg-muted rounded-lg p-3">
                  <div className="text-lg font-semibold">{nonTruncatedByTermination[termType]}</div>
                  <div className="text-xs text-muted-foreground">{termType}</div>
                </div>
              ))}
            </div>
            {(results.truncated_paths ?? 0) > 0 && (
              <div className="mt-3 text-sm text-muted-foreground">
                {results.truncated_paths} paths were truncated due to loop limits
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Paths preview */}
      {results.paths && results.paths.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>Path Preview</span>
              {truncatedInfo && (
                <Badge variant="outline" className="font-normal">
                  Showing {displayedPaths} of {truncatedInfo}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {results.paths.slice(0, 5).map((path) => (
                <div
                  key={path.path_number}
                  className="text-xs bg-muted p-2 rounded"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="outline" className="font-mono">
                      #{path.path_number}
                    </Badge>
                    {path.is_pairing_path && (
                      <Badge variant="secondary" className="text-xs">Pairing</Badge>
                    )}
                  </div>
                  <div className="text-muted-foreground pl-2 font-mono text-xs leading-relaxed">
                    {path.nodes.map((node, idx) => (
                      <span key={idx}>
                        {idx > 0 && <span className="text-muted-foreground/50">{' → '}</span>}
                        {idx > 0 && <br />}
                        <span>{node}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {displayedPaths > 5 && (
                <div className="text-xs text-muted-foreground text-center py-1">
                  ... and {displayedPaths - 5} more paths in preview
                </div>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Download the HTML report for complete path enumeration and expected file patterns.
            </p>
          </CardContent>
        </Card>
      )}
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
        // Detect display_graph mode by checking for paths array (display_graph)
        // vs consistency_counts (collection validation mode)
        const pipelineResults = result.results as unknown as Record<string, unknown>
        if ('paths' in pipelineResults || 'total_paths' in pipelineResults) {
          return (
            <DisplayGraphResultsView
              results={result.results as DisplayGraphResults & { _truncated?: Record<string, number> }}
            />
          )
        }
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
              <Badge variant="outline">
                Pipeline: {result.pipeline_name}
                {result.pipeline_version && ` v${result.pipeline_version}`}
              </Badge>
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
