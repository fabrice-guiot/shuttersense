/**
 * AgentsPage Component
 *
 * Lists all registered agents with status, rename, and revoke functionality.
 * Note: This page is NOT in the sidebar per spec - accessed via /agents route or header badge.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T048
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2, MoreHorizontal, RefreshCw, Loader2, Eye, ExternalLink, Wand2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { useAgents, useAgentStats, useRegistrationTokens } from '@/hooks/useAgents'
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge'
import { AgentDetailsDialog } from '@/components/agents/AgentDetailsDialog'
import { RegistrationTokenDialog } from '@/components/agents/RegistrationTokenDialog'
import { AgentSetupWizardDialog } from '@/components/agents/AgentSetupWizardDialog'
import { GuidBadge } from '@/components/GuidBadge'
import { formatDateTime } from '@/utils/dateFormat'
import { AuditTrailPopover } from '@/components/audit'
import type { Agent } from '@/contracts/api/agent-api'

export default function AgentsPage() {
  const { agents, loading, error, fetchAgents, updateAgent, revokeAgent } = useAgents()
  const { stats, refetch: refetchStats } = useAgentStats()
  const { createToken } = useRegistrationTokens(false) // Don't auto-fetch tokens
  const { setStats } = useHeaderStats()

  // Dialog states
  const [wizardOpen, setWizardOpen] = useState(false)
  const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false)
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [newName, setNewName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  // Update header stats
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Agents', value: stats.total_agents },
        { label: 'Online', value: stats.online_agents },
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  const handleViewDetails = (agent: Agent) => {
    setSelectedAgent(agent)
    setDetailsDialogOpen(true)
  }

  const handleRename = (agent: Agent) => {
    setSelectedAgent(agent)
    setNewName(agent.name)
    setFormError(null)
    setRenameDialogOpen(true)
  }

  const handleRenameSubmit = async () => {
    if (!selectedAgent || !newName.trim()) return

    setFormError(null)
    try {
      await updateAgent(selectedAgent.guid, { name: newName.trim() })
      setRenameDialogOpen(false)
      setSelectedAgent(null)
      refetchStats()
    } catch (err: any) {
      setFormError(err.userMessage || 'Failed to rename agent')
    }
  }

  const handleRevoke = (agent: Agent) => {
    setSelectedAgent(agent)
    setRevokeDialogOpen(true)
  }

  const handleRevokeConfirm = async () => {
    if (!selectedAgent) return

    try {
      await revokeAgent(selectedAgent.guid)
      setRevokeDialogOpen(false)
      setSelectedAgent(null)
      refetchStats()
    } catch (err) {
      // Error handled by hook
    }
  }

  const handleRefresh = () => {
    fetchAgents()
    refetchStats()
  }

  const agentColumns: ColumnDef<Agent>[] = [
    {
      header: 'Name',
      cell: (agent) => (
        <div className="flex flex-col gap-1">
          <span className="font-medium">{agent.name}</span>
          <GuidBadge guid={agent.guid} />
        </div>
      ),
      cardRole: 'title',
    },
    {
      header: 'Status',
      cell: (agent) => (
        <>
          <AgentStatusBadge status={agent.status} />
          {agent.error_message && (
            <p className="text-xs text-destructive mt-1">{agent.error_message}</p>
          )}
        </>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Load',
      cell: (agent) => agent.running_jobs_count > 0 ? (
        <Badge variant="info">
          {agent.running_jobs_count} {agent.running_jobs_count === 1 ? 'job' : 'jobs'}
        </Badge>
      ) : (
        <span className="text-muted-foreground text-sm">Idle</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Hostname',
      cell: (agent) => (
        <div className="flex flex-col min-w-0">
          <span className="truncate" title={agent.hostname}>{agent.hostname}</span>
          <span className="text-xs text-muted-foreground truncate" title={agent.os_info}>{agent.os_info}</span>
        </div>
      ),
      cardRole: 'subtitle',
    },
    {
      header: 'Version',
      cell: (agent) => (
        <span className="text-sm font-mono block truncate max-w-[200px]" title={agent.version}>
          {agent.version}
        </span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Last Heartbeat',
      cell: (agent) => agent.last_heartbeat ? (
        <span className="text-sm">{formatDateTime(agent.last_heartbeat)}</span>
      ) : (
        <span className="text-muted-foreground">Never</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Modified',
      cell: (agent) => (
        <AuditTrailPopover audit={agent.audit} fallbackTimestamp={agent.created_at} />
      ),
      cellClassName: 'text-muted-foreground',
      cardRole: 'hidden',
    },
    {
      header: '',
      headerClassName: 'w-[50px]',
      cell: (agent) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
              <span className="sr-only">Actions</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link to={`/agents/${agent.guid}`}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Open Detail Page
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleViewDetails(agent)}>
              <Eye className="h-4 w-4 mr-2" />
              Quick View
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleRename(agent)}>
              <Pencil className="h-4 w-4 mr-2" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handleRevoke(agent)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Revoke
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
      cardRole: 'action',
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row */}
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
        <Button variant="outline" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
        <Button variant="success" onClick={() => setWizardOpen(true)}>
          <Wand2 className="h-4 w-4 mr-2" />
          Agent Setup
        </Button>
        <Button onClick={() => setTokenDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Registration Token
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Agents Table */}
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Registered Agents</CardTitle>
          <CardDescription>
            Agents running on local machines that can execute analysis jobs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && agents.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <ResponsiveTable
              data={agents}
              columns={agentColumns}
              keyField="guid"
              emptyState={
                <div className="text-center py-8 text-muted-foreground">
                  <p>No agents registered yet.</p>
                  <p className="text-sm mt-2">
                    Create a registration token and use it to register an agent.
                  </p>
                </div>
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Agent Setup Wizard Dialog */}
      <AgentSetupWizardDialog
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        createToken={createToken}
        onComplete={() => {
          fetchAgents()
          refetchStats()
        }}
      />

      {/* Registration Token Dialog */}
      <RegistrationTokenDialog
        open={tokenDialogOpen}
        onOpenChange={setTokenDialogOpen}
        onCreateToken={createToken}
      />

      {/* Agent Details Dialog */}
      <AgentDetailsDialog
        agent={selectedAgent}
        open={detailsDialogOpen}
        onOpenChange={setDetailsDialogOpen}
      />

      {/* Rename Dialog */}
      <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Agent</DialogTitle>
            <DialogDescription>
              Enter a new name for the agent &quot;{selectedAgent?.name}&quot;.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="agent-name">Name</Label>
            <Input
              id="agent-name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              className="mt-2"
            />
            {formError && (
              <Alert variant="destructive" className="mt-4">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleRenameSubmit} disabled={!newName.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Confirmation Dialog */}
      <AlertDialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke Agent</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to revoke &quot;{selectedAgent?.name}&quot;? This agent will no
              longer be able to connect to the server or execute jobs.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRevokeConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
