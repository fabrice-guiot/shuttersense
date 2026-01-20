import { useState, useMemo } from 'react'
import { Bot, CloudCheck, Edit, Trash2 } from 'lucide-react'
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
import type { Connector, ConnectorType, CredentialLocation } from '@/contracts/api/connector-api'
import type { Agent } from '@/contracts/api/agent-api'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/utils/dateFormat'

// ============================================================================
// Component Props
// ============================================================================

export interface ConnectorListProps {
  connectors: Connector[]
  loading: boolean
  onEdit: (connector: Connector) => void
  onDelete: (connector: Connector) => void
  onTest: (connector: Connector) => void
  /** List of agents (to show which have credentials for agent-based connectors) */
  agents?: Agent[]
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

const CREDENTIAL_LOCATION_LABELS: Record<CredentialLocation, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  server: { label: 'Server', variant: 'default' },
  agent: { label: 'Agent', variant: 'secondary' },
  pending: { label: 'Pending Config', variant: 'outline' }
}

function getCredentialLocationDisplay(location: CredentialLocation): { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' } {
  return CREDENTIAL_LOCATION_LABELS[location] || { label: location, variant: 'outline' }
}

/**
 * Get agents that have credentials for a specific connector.
 * Agents report connector credentials as capabilities with format "connector:{guid}"
 */
function getAgentsWithCredentials(connectorGuid: string, agents: Agent[]): Agent[] {
  const capability = `connector:${connectorGuid}`
  return agents.filter(agent => agent.capabilities.includes(capability))
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
  agents = [],
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
                <TableHead>Credentials</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConnectors.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
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
                      {(() => {
                        const { label, variant } = getCredentialLocationDisplay(connector.credential_location)
                        const agentsWithCreds = connector.credential_location !== 'server'
                          ? getAgentsWithCredentials(connector.guid, agents)
                          : []

                        return (
                          <div className="flex items-center gap-2">
                            <Badge variant={variant}>{label}</Badge>
                            {connector.credential_location === 'agent' && agentsWithCreds.length > 0 && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="flex items-center gap-1 text-xs text-muted-foreground cursor-help">
                                      <Bot className="h-3 w-3" />
                                      {agentsWithCreds.length}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-xs">
                                    <div className="text-sm">
                                      <div className="font-medium mb-1">Agents with credentials:</div>
                                      <ul className="list-none space-y-0.5">
                                        {agentsWithCreds.map(agent => (
                                          <li key={agent.guid} className="flex items-center gap-1">
                                            <span className={cn(
                                              "h-2 w-2 rounded-full",
                                              agent.status === 'online' ? "bg-green-500" : "bg-gray-400"
                                            )} />
                                            {agent.name}
                                            <span className="text-muted-foreground">({agent.hostname})</span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                            {connector.credential_location === 'pending' && (
                              <span className="text-xs text-amber-600 dark:text-amber-400">
                                Needs config
                              </span>
                            )}
                          </div>
                        )
                      })()}
                    </TableCell>
                    <TableCell>
                      <Badge variant={connector.is_active ? 'default' : 'outline'}>
                        {connector.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDateTime(connector.created_at)}
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
                                disabled={connector.credential_location !== 'server'}
                                aria-label="Test Connection"
                              >
                                <CloudCheck className="h-4 w-4" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              {connector.credential_location === 'server'
                                ? 'Test Connection'
                                : connector.credential_location === 'pending'
                                  ? 'Cannot test: credentials not configured'
                                  : 'Cannot test from server: credentials on agent'}
                            </TooltipContent>
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
