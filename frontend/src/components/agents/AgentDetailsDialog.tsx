/**
 * AgentDetailsDialog Component
 *
 * Dialog for displaying detailed information about an agent including
 * capabilities and authorized roots.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 6b)
 */

import { Bot, FolderOpen, Wrench, Server, Clock, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge'
import { GuidBadge } from '@/components/GuidBadge'
import { formatDateTime } from '@/utils/dateFormat'
import { AuditTrailSection } from '@/components/audit'
import type { Agent } from '@/contracts/api/agent-api'

interface AgentDetailsDialogProps {
  agent: Agent | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * AgentDetailsDialog displays comprehensive information about an agent.
 */
export function AgentDetailsDialog({ agent, open, onOpenChange }: AgentDetailsDialogProps) {
  if (!agent) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent Details
          </DialogTitle>
          <DialogDescription>
            Detailed information about the agent and its configuration.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Info Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-muted-foreground">Name</h4>
              <span className="font-medium">{agent.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-muted-foreground">GUID</h4>
              <GuidBadge guid={agent.guid} />
            </div>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-muted-foreground">Status</h4>
              <AgentStatusBadge
                status={agent.status}
                isOutdated={agent.is_outdated}
                hasMissingPlatform={!agent.platform}
              />
            </div>
            {agent.error_message && (
              <div className="flex items-start gap-2 p-2 rounded-md bg-destructive/10 text-destructive text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>{agent.error_message}</span>
              </div>
            )}
          </div>

          {/* System Info Section */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Server className="h-4 w-4" />
              System Information
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-muted-foreground">Hostname</span>
              <span className="font-mono">{agent.hostname}</span>
              <span className="text-muted-foreground">OS</span>
              <span>{agent.os_info}</span>
              <span className="text-muted-foreground">Version</span>
              <span className="font-mono">{agent.version}</span>
              <span className="text-muted-foreground">Last Heartbeat</span>
              <span>
                {agent.last_heartbeat ? formatDateTime(agent.last_heartbeat) : 'Never'}
              </span>
              <span className="text-muted-foreground">Registered</span>
              <span>{formatDateTime(agent.created_at)}</span>
            </div>
          </div>

          {/* Capabilities Section */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Wrench className="h-4 w-4" />
              Capabilities
            </div>
            {agent.capabilities.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {agent.capabilities.map(capability => (
                  <Badge key={capability} variant="secondary" className="font-mono text-xs">
                    {capability}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No capabilities reported</p>
            )}
          </div>

          {/* Authorized Roots Section */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex items-center gap-2 text-sm font-medium">
              <FolderOpen className="h-4 w-4" />
              Authorized Roots
            </div>
            {agent.authorized_roots.length > 0 ? (
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {agent.authorized_roots.map(root => (
                  <div
                    key={root}
                    className="flex items-center gap-2 p-2 rounded-md bg-muted text-sm font-mono"
                  >
                    <FolderOpen className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                    <span className="truncate" title={root}>
                      {root}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No authorized roots configured</p>
            )}
          </div>

          {/* Current Job */}
          {agent.current_job_guid && (
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Clock className="h-4 w-4" />
                Current Job
              </div>
              <GuidBadge guid={agent.current_job_guid} />
            </div>
          )}

          <AuditTrailSection audit={agent.audit} />
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default AgentDetailsDialog
