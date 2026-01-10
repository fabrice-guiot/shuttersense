import { useState, useMemo } from 'react'
import { CloudCheck, Edit, Trash2 } from 'lucide-react'
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
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import type { Connector, ConnectorType } from '@/contracts/api/connector-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Component Props
// ============================================================================

export interface ConnectorListProps {
  connectors: Connector[]
  loading: boolean
  onEdit: (connector: Connector) => void
  onDelete: (connector: Connector) => void
  onTest: (connector: Connector) => void
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

const CONNECTOR_TYPE_LABELS: Record<ConnectorType, string> = {
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

// Connector types still in beta/QA - remove from this set once QA'd
const BETA_CONNECTOR_TYPES: Set<ConnectorType> = new Set(['gcs', 'smb'])

function getConnectorTypeLabel(type: ConnectorType): string {
  return CONNECTOR_TYPE_LABELS[type] || type
}

function isBetaConnectorType(type: ConnectorType): boolean {
  return BETA_CONNECTOR_TYPES.has(type)
}

function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString()
}

// ============================================================================
// Component
// ============================================================================

export function ConnectorList({
  connectors,
  loading,
  onEdit,
  onDelete,
  onTest,
  className
}: ConnectorListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    connector: Connector | null
  }>({ open: false, connector: null })

  // Filter state
  const [typeFilter, setTypeFilter] = useState<ConnectorType | 'ALL'>('ALL')
  const [activeOnly, setActiveOnly] = useState(false)

  // Apply filters
  const filteredConnectors = useMemo(() => {
    return connectors.filter((c) => {
      // Type filter
      if (typeFilter !== 'ALL' && c.type !== typeFilter) {
        return false
      }
      // Active only filter
      if (activeOnly && !c.is_active) {
        return false
      }
      return true
    })
  }, [connectors, typeFilter, activeOnly])

  const handleDeleteClick = (connector: Connector) => {
    setDeleteDialog({ open: true, connector })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.connector) {
      onDelete(deleteDialog.connector)
      setDeleteDialog({ open: false, connector: null })
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialog({ open: false, connector: null })
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

  if (connectors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No connectors found</p>
      </div>
    )
  }

  return (
    <>
      <div className={cn('flex flex-col gap-4', className)}>
        {/* Filters Section */}
        <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-end">
          {/* Type Filter */}
          <div className="flex flex-col gap-2 flex-1">
            <Label htmlFor="type-filter" className="text-sm font-medium">
              Type
            </Label>
            <Select
              value={typeFilter}
              onValueChange={(value) => setTypeFilter(value as ConnectorType | 'ALL')}
            >
              <SelectTrigger id="type-filter" className="w-full">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Types</SelectItem>
                <SelectItem value="s3">
                  <span className="flex items-center gap-2">
                    Amazon S3
                    {isBetaConnectorType('s3') && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        Beta
                      </span>
                    )}
                  </span>
                </SelectItem>
                <SelectItem value="gcs">
                  <span className="flex items-center gap-2">
                    Google Cloud Storage
                    {isBetaConnectorType('gcs') && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        Beta
                      </span>
                    )}
                  </span>
                </SelectItem>
                <SelectItem value="smb">
                  <span className="flex items-center gap-2">
                    SMB/CIFS
                    {isBetaConnectorType('smb') && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        Beta
                      </span>
                    )}
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Active Only Filter */}
          <div className="flex items-center gap-2 flex-1">
            <Checkbox
              id="active-only"
              checked={activeOnly}
              onCheckedChange={(checked) => setActiveOnly(checked === true)}
            />
            <Label
              htmlFor="active-only"
              className="text-sm font-medium cursor-pointer"
            >
              Active Only
            </Label>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-md border border-border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConnectors.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    No connectors match the current filters
                  </TableCell>
                </TableRow>
              ) : (
                filteredConnectors.map((connector) => (
                  <TableRow key={connector.guid}>
                    <TableCell className="font-medium">{connector.name}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {getConnectorTypeLabel(connector.type)}
                        </Badge>
                        {isBetaConnectorType(connector.type) && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            Beta
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={connector.is_active ? 'default' : 'outline'}>
                        {connector.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(connector.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onTest(connector)}
                                aria-label="Test Connection"
                              >
                                <CloudCheck className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Test Connection</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onEdit(connector)}
                                aria-label="Edit Connector"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Edit Connector</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeleteClick(connector)}
                                aria-label="Delete Connector"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Delete Connector</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={handleDeleteCancel}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Connector</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteDialog.connector?.name}"?
              If collections reference this connector, deletion will fail.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleDeleteCancel}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
