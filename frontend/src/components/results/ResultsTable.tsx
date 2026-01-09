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
  Search,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
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
import { cn } from '@/lib/utils'

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
  CANCELLED: { label: 'Cancelled', variant: 'secondary' }
}

// Tool display names
const TOOL_LABELS: Record<ToolType, string> = {
  photostats: 'PhotoStats',
  photo_pairing: 'Photo Pairing',
  pipeline_validation: 'Pipeline Validation'
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

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString()
  }

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
      {results.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileText className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-muted-foreground">No analysis results found</p>
        </div>
      ) : (
        <div className="rounded-md border border-border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Collection</TableHead>
                <TableHead>Tool</TableHead>
                <TableHead>Pipeline</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Files</TableHead>
                <TableHead>Issues</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.id}>
                  <TableCell className="font-medium">
                    {result.collection_name ?? (
                      <span className="text-muted-foreground italic">Pipeline only</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {TOOL_LABELS[result.tool]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {result.pipeline_name ? (
                      <span className="text-sm" title={`v${result.pipeline_version}`}>
                        {result.pipeline_name}
                        <span className="text-muted-foreground text-xs ml-1">
                          v{result.pipeline_version}
                        </span>
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-sm">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_CONFIG[result.status].variant}>
                      {STATUS_CONFIG[result.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell>{result.files_scanned ?? '-'}</TableCell>
                  <TableCell>{result.issues_found ?? '-'}</TableCell>
                  <TableCell>{formatDuration(result.duration_seconds)}</TableCell>
                  <TableCell>{formatDate(result.completed_at)}</TableCell>
                  <TableCell>
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
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
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
              {deleteDialog.result?.collection_name
                ? ` for "${deleteDialog.result.collection_name}"`
                : ' (Pipeline only)'}
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
