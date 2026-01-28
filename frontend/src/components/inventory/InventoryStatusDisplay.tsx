/**
 * InventoryStatusDisplay Component
 *
 * Displays the current inventory validation and import status for a connector.
 * Shows validation state, last import timestamp, folder counts, and current job progress.
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { CheckCircle, XCircle, Loader2, Clock, FolderOpen, AlertCircle, Archive, FileText } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { formatDateTime, formatRelativeTime } from '@/utils/dateFormat'
import type { InventoryStatus, InventoryValidationStatus } from '@/contracts/api/inventory-api'

// ============================================================================
// Component Props
// ============================================================================

export interface InventoryStatusDisplayProps {
  /** Inventory status data */
  status: InventoryStatus | null
  /** Loading state */
  loading?: boolean
  /** Additional CSS class */
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

function getValidationStatusConfig(status: InventoryValidationStatus | null): {
  label: string
  variant: 'default' | 'secondary' | 'outline' | 'destructive'
  icon: React.ReactNode
} {
  switch (status) {
    case 'validated':
      return {
        label: 'Validated',
        variant: 'default',
        icon: <CheckCircle className="h-3.5 w-3.5" />
      }
    case 'validating':
      return {
        label: 'Validating',
        variant: 'secondary',
        icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />
      }
    case 'failed':
      return {
        label: 'Validation Failed',
        variant: 'destructive',
        icon: <XCircle className="h-3.5 w-3.5" />
      }
    case 'pending':
      return {
        label: 'Pending',
        variant: 'outline',
        icon: <Clock className="h-3.5 w-3.5" />
      }
    default:
      return {
        label: 'Not Configured',
        variant: 'outline',
        icon: <AlertCircle className="h-3.5 w-3.5" />
      }
  }
}

// ============================================================================
// Component
// ============================================================================

export function InventoryStatusDisplay({
  status,
  loading = false,
  className
}: InventoryStatusDisplayProps) {
  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 text-muted-foreground', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading status...</span>
      </div>
    )
  }

  if (!status) {
    return (
      <div className={cn('text-sm text-muted-foreground', className)}>
        No inventory configuration
      </div>
    )
  }

  const validationConfig = getValidationStatusConfig(status.validation_status)

  return (
    <div className={cn('space-y-3', className)}>
      {/* Validation Status */}
      <div className="flex items-center gap-2">
        <Badge variant={validationConfig.variant} className="gap-1">
          {validationConfig.icon}
          {validationConfig.label}
        </Badge>
      </div>

      {/* Latest Manifest - shown when validated */}
      {status.validation_status === 'validated' && status.latest_manifest && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <FileText className="h-4 w-4" />
          <span>Latest manifest: <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono">{status.latest_manifest}</code></span>
        </div>
      )}

      {/* Validation Error */}
      {status.validation_status === 'failed' && status.validation_error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          <p className="font-medium">Validation Error</p>
          <p className="mt-1">{status.validation_error}</p>
        </div>
      )}

      {/* Current Job Progress */}
      {status.current_job && (
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm font-medium">
                {status.current_job.phase === 'folder_extraction' && 'Extracting folders...'}
                {status.current_job.phase === 'file_info_population' && 'Populating file info...'}
                {status.current_job.phase === 'delta_detection' && 'Detecting changes...'}
                {!status.current_job.phase && 'Processing...'}
              </span>
            </div>
            <span className="text-sm text-muted-foreground">
              {status.current_job.progress_percentage}%
            </span>
          </div>
          <Progress value={status.current_job.progress_percentage} className="mt-2 h-2" />
        </div>
      )}

      {/* Stats */}
      {status.validation_status === 'validated' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{status.folder_count}</p>
              <p className="text-xs text-muted-foreground">Total Folders</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Archive className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{status.mapped_folder_count}</p>
              <p className="text-xs text-muted-foreground">Mapped to Collections</p>
            </div>
          </div>
        </div>
      )}

      {/* Timestamps */}
      {(status.last_import_at || status.next_scheduled_at) && (
        <div className="space-y-1 text-sm text-muted-foreground">
          {status.last_import_at && (
            <p>
              Last import: {formatRelativeTime(status.last_import_at)}
              <span className="ml-1 text-xs">({formatDateTime(status.last_import_at)})</span>
            </p>
          )}
          {status.next_scheduled_at && (
            <p>
              Next scheduled: {formatRelativeTime(status.next_scheduled_at)}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default InventoryStatusDisplay
