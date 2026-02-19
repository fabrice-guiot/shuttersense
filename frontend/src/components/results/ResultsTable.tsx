/**
 * Results Table Component
 *
 * Displays analysis results in a filterable, paginated table
 */

import { useState } from 'react'
import {
  Trash2,
  Download,
  Eye,
  FileText,
  ChevronLeft,
  ChevronRight,
  Copy,
  FolderOpen,
  Plug,
  Camera,
  Workflow
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import type {
  AnalysisResultSummary,
  ResultStatus,
  ToolType,
  ResultListQueryParams
} from '@/contracts/api/results-api'
import type { TargetEntityType } from '@/contracts/api/target-api'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/utils/dateFormat'

// ============================================================================
// Types
// ============================================================================

interface ResultsTableProps {
  results: AnalysisResultSummary[]
  total: number
  page: number
  limit: number
  loading: boolean
  onPageChange: (page: number) => void
  onLimitChange: (limit: number) => void
  onFiltersChange: (filters: ResultListQueryParams) => void
  onView: (result: AnalysisResultSummary) => void
  onDelete: (result: AnalysisResultSummary) => void
  onDownloadReport: (result: AnalysisResultSummary) => void
  className?: string
}

// Status display configuration
const STATUS_CONFIG: Record<
  ResultStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' }
> = {
  COMPLETED: { label: 'Completed', variant: 'success' },
  FAILED: { label: 'Failed', variant: 'destructive' },
  CANCELLED: { label: 'Cancelled', variant: 'secondary' },
  NO_CHANGE: { label: 'No Change', variant: 'default' }
}

// Target entity type icons (Issue #110)
const TARGET_ICONS: Record<TargetEntityType, LucideIcon> = {
  collection: FolderOpen,
  connector: Plug,
  pipeline: Workflow,
  camera: Camera,
}

// Tool display names
const TOOL_LABELS: Record<ToolType, string> = {
  photostats: 'PhotoStats',
  photo_pairing: 'Photo Pairing',
  pipeline_validation: 'Pipeline Validation',
  collection_test: 'Collection Test',
  inventory_validate: 'Inventory Validation',
  inventory_import: 'Inventory Import'
}

// ============================================================================
// Component
// ============================================================================

export function ResultsTable({
  results,
  total,
  page,
  limit,
  loading,
  onPageChange,
  onLimitChange,
  onFiltersChange,
  onView,
  onDelete,
  onDownloadReport,
  className
}: ResultsTableProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    result: AnalysisResultSummary | null
  }>({ open: false, result: null })

  const [toolFilter, setToolFilter] = useState<ToolType | 'ALL'>('ALL')
  const [statusFilter, setStatusFilter] = useState<ResultStatus | 'ALL'>('ALL')

  const totalPages = Math.ceil(total / limit)

  const handleToolFilterChange = (value: string) => {
    setToolFilter(value as ToolType | 'ALL')
    const filters: ResultListQueryParams = {}
    if (value !== 'ALL') filters.tool = value as ToolType
    if (statusFilter !== 'ALL') filters.status = statusFilter
    onFiltersChange(filters)
  }

  const handleStatusFilterChange = (value: string) => {
    setStatusFilter(value as ResultStatus | 'ALL')
    const filters: ResultListQueryParams = {}
    if (toolFilter !== 'ALL') filters.tool = toolFilter
    if (value !== 'ALL') filters.status = value as ResultStatus
    onFiltersChange(filters)
  }

  const handleDeleteClick = (result: AnalysisResultSummary) => {
    setDeleteDialog({ open: true, result })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.result) {
      onDelete(deleteDialog.result)
      setDeleteDialog({ open: false, result: null })
    }
  }

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }


  const resultColumns: ColumnDef<AnalysisResultSummary>[] = [
    {
      header: 'Target',
      cell: (result) => {
        // Use polymorphic target if available, fall back to legacy fields
        const entityType = result.target?.entity_type
        const entityName = result.target?.entity_name ?? result.collection_name ?? result.connector_name
        const Icon = entityType ? TARGET_ICONS[entityType] ?? FolderOpen : (result.connector_name ? Plug : FolderOpen)

        return entityName ? (
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{entityName}</span>
          </div>
        ) : (
          <span className="text-muted-foreground text-sm">-</span>
        )
      },
      cellClassName: 'font-medium',
      cardRole: 'title',
    },
    {
      header: 'Tool',
      cell: (result) => (
        <Badge variant="secondary">
          {TOOL_LABELS[result.tool]}
        </Badge>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Pipeline',
      cell: (result) => {
        // Prefer context pipeline info (Issue #110), fall back to legacy fields
        const pipeName = result.context?.pipeline?.name ?? result.pipeline_name
        const pipeVersion = result.context?.pipeline?.version ?? result.pipeline_version
        return pipeName ? (
          <span className="text-sm" title={pipeVersion != null ? `v${pipeVersion}` : undefined}>
            {pipeName}
            {pipeVersion != null && (
              <span className="text-muted-foreground text-xs ml-1">
                v{pipeVersion}
              </span>
            )}
          </span>
        ) : (
          <span className="text-muted-foreground text-sm">-</span>
        )
      },
      cardRole: 'detail',
    },
    {
      header: 'Status',
      cell: (result) => (
        <div className="flex items-center gap-1.5">
          <Badge variant={STATUS_CONFIG[result.status].variant}>
            {STATUS_CONFIG[result.status].label}
          </Badge>
          {result.no_change_copy && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  References a previous result (storage optimized)
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Files',
      cell: (result) => result.files_scanned ?? '-',
      cardRole: 'detail',
    },
    {
      header: 'Issues',
      cell: (result) => result.issues_found ?? '-',
      cardRole: 'detail',
    },
    {
      header: 'Duration',
      cell: (result) => formatDuration(result.duration_seconds),
      cardRole: 'detail',
    },
    {
      header: 'Completed',
      cell: (result) => formatRelativeTime(result.completed_at),
      cardRole: 'detail',
    },
    {
      header: 'Created by',
      cell: (result) => {
        const user = result.audit?.created_by
        if (!user) return <span className="text-muted-foreground text-sm">{'\u2014'}</span>
        return <span className="text-sm">{user.display_name || user.email || '\u2014'}</span>
      },
      cellClassName: 'text-muted-foreground',
      cardRole: 'hidden',
    },
    {
      header: 'Actions',
      headerClassName: 'text-right',
      cell: (result) => (
        <div className="flex justify-end gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onView(result)}
                >
                  <Eye className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>View Details</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {result.has_report && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDownloadReport(result)}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download Report</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDeleteClick(result)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete Result</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ),
      cardRole: 'action',
    },
  ]

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div
          role="status"
          className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
        />
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Tool:</span>
          <Select value={toolFilter} onValueChange={handleToolFilterChange}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Tools</SelectItem>
              {Object.entries(TOOL_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Status</SelectItem>
              {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  {config.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <ResponsiveTable
        data={results}
        columns={resultColumns}
        keyField="guid"
        emptyState={
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground">No analysis results found</p>
          </div>
        }
      />

      {/* Pagination */}
      {total > 0 && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Rows per page:</span>
            <Select
              value={limit.toString()}
              onValueChange={(value) => onLimitChange(parseInt(value, 10))}
            >
              <SelectTrigger className="w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-sm text-muted-foreground">
              {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-sm">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={() => setDeleteDialog({ open: false, result: null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Result</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this analysis result
              {(deleteDialog.result?.target?.entity_name ?? deleteDialog.result?.collection_name)
                ? ` for "${deleteDialog.result?.target?.entity_name ?? deleteDialog.result?.collection_name}"`
                : ''}
              ? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, result: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
