/**
 * AgentStatusBadge Component
 *
 * Displays agent status with appropriate styling for each state.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T050
 */

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AgentStatus } from '@/contracts/api/agent-api'

interface AgentStatusBadgeProps {
  status: AgentStatus
  className?: string
  showLabel?: boolean
}

/**
 * Maps agent status to display label
 */
const STATUS_LABELS: Record<AgentStatus, string> = {
  online: 'Online',
  offline: 'Offline',
  error: 'Error',
  revoked: 'Revoked',
}

/**
 * Maps agent status to badge variant
 */
const STATUS_VARIANTS: Record<AgentStatus, 'success' | 'secondary' | 'destructive' | 'outline'> = {
  online: 'success',
  offline: 'secondary',
  error: 'destructive',
  revoked: 'outline',
}

/**
 * AgentStatusBadge displays the current status of an agent.
 *
 * Status states:
 * - online: Agent is connected and responsive (green)
 * - offline: Agent hasn't sent heartbeat recently (gray)
 * - error: Agent reported an error state (red)
 * - revoked: Agent access has been revoked (outlined)
 */
export function AgentStatusBadge({
  status,
  className,
  showLabel = true,
}: AgentStatusBadgeProps) {
  const variant = STATUS_VARIANTS[status] || 'secondary'
  const label = STATUS_LABELS[status] || status

  return (
    <Badge
      variant={variant}
      className={cn(
        // Add a pulsing indicator dot for online status
        status === 'online' && 'relative pl-5',
        className
      )}
    >
      {status === 'online' && (
        <span className="absolute left-1.5 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-green-400 animate-pulse" />
      )}
      {showLabel && label}
    </Badge>
  )
}

export default AgentStatusBadge
