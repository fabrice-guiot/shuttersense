/**
 * AgentPoolStatus Component
 *
 * Displays agent pool status badge in the header.
 * - Red "Offline (X)" when no agents online, X = total registered agents
 * - Blue "Idle (X)" when agents online but no jobs, X = online agent count
 * - Green "Running (X)" when jobs running, X = running job count
 * Clickable to navigate to /agents page.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 4)
 * Task: T064
 */

import { useNavigate } from 'react-router-dom'
import { Bot } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useAgentPoolStatus } from '@/hooks/useAgentPoolStatus'
import type { AgentPoolStatusResponse } from '@/contracts/api/agent-api'

// ============================================================================
// Types
// ============================================================================

export interface AgentPoolStatusProps {
  className?: string
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Get badge variant and styles based on pool status
 */
function getBadgeStyles(status: AgentPoolStatusResponse['status']): string {
  switch (status) {
    case 'running':
      return 'bg-success text-success-foreground hover:bg-success/90'
    case 'idle':
      return 'bg-info text-info-foreground hover:bg-info/90'
    case 'offline':
    default:
      return 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
  }
}

/**
 * Get status label text
 */
function getStatusLabel(status: AgentPoolStatusResponse['status']): string {
  switch (status) {
    case 'running':
      return 'Running'
    case 'idle':
      return 'Idle'
    case 'offline':
    default:
      return 'Offline'
  }
}

/**
 * Get the count to display in the badge
 * - Offline: total registered agents (online + offline)
 * - Idle: online agent count
 * - Running: running jobs count
 */
function getBadgeCount(poolStatus: AgentPoolStatusResponse): number {
  switch (poolStatus.status) {
    case 'running':
      return poolStatus.running_jobs_count
    case 'idle':
      return poolStatus.online_count
    case 'offline':
    default:
      return poolStatus.online_count + poolStatus.offline_count
  }
}

/**
 * Get tooltip text based on pool status
 */
function getTooltipText(poolStatus: AgentPoolStatusResponse): string {
  const { online_count, offline_count, idle_count, running_jobs_count, status } = poolStatus
  const totalAgents = online_count + offline_count

  if (status === 'offline') {
    if (totalAgents === 0) {
      return 'No agents registered'
    }
    return `All ${totalAgents} agent${totalAgents !== 1 ? 's' : ''} offline`
  }

  const parts: string[] = []
  parts.push(`${online_count} agent${online_count !== 1 ? 's' : ''} online`)

  if (running_jobs_count > 0) {
    parts.push(`${running_jobs_count} job${running_jobs_count !== 1 ? 's' : ''} running`)
  } else if (idle_count > 0) {
    parts.push(`all idle`)
  }

  if (offline_count > 0) {
    parts.push(`${offline_count} offline`)
  }

  return parts.join(', ')
}

// ============================================================================
// Component
// ============================================================================

export function AgentPoolStatus({ className }: AgentPoolStatusProps) {
  const navigate = useNavigate()
  const { poolStatus, loading, error } = useAgentPoolStatus()

  const handleClick = () => {
    navigate('/agents')
  }

  // Don't render if loading initial data
  if (loading && !poolStatus) {
    return null
  }

  // Don't render if error and no data
  if (error && !poolStatus) {
    return null
  }

  // Default status when no data
  const status = poolStatus?.status || 'offline'
  const count = poolStatus ? getBadgeCount(poolStatus) : 0
  const label = getStatusLabel(status)

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleClick}
            className={cn(
              'rounded-md hover:opacity-90 transition-opacity',
              className
            )}
            aria-label="Agent pool status"
          >
            <Badge
              className={cn(
                'flex items-center gap-1 xl:gap-1.5 px-1.5 xl:px-2.5 py-1 text-xs font-medium cursor-pointer',
                getBadgeStyles(status)
              )}
            >
              <Bot className="h-3.5 w-3.5" />
              <span className="hidden xl:inline">{label}</span>
              <span className="opacity-80">{count}</span>
            </Badge>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <p>{poolStatus ? getTooltipText(poolStatus) : 'No agents registered'}</p>
          <p className="text-xs text-muted-foreground mt-1">Click to manage agents</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export default AgentPoolStatus
