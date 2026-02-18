/**
 * AgentStatusBadge Component
 *
 * Displays agent status with appropriate styling for each state.
 * Supports derived "outdated" state when agent is online but running
 * an old version with no active jobs.
 *
 * Priority: error > running > outdated > online > offline > revoked
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Issue #242 - Outdated Agent Detection
 */

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AgentStatus } from '@/contracts/api/agent-api'
import {
  AGENT_STATUS_LABELS,
  AGENT_STATUS_BADGE_VARIANT,
  AGENT_OUTDATED_LABEL,
  AGENT_OUTDATED_BADGE_VARIANT,
} from '@/contracts/domain-labels'

interface AgentStatusBadgeProps {
  status: AgentStatus
  isOutdated?: boolean
  runningJobsCount?: number
  className?: string
  showLabel?: boolean
}

/**
 * Determine the effective display state for the badge.
 *
 * Priority: error > running > outdated > online > offline > revoked
 */
function getEffectiveState(
  status: AgentStatus,
  isOutdated: boolean,
  runningJobsCount: number
): { label: string; variant: string; showPulse: boolean } {
  if (status === 'error') {
    return {
      label: AGENT_STATUS_LABELS.error,
      variant: AGENT_STATUS_BADGE_VARIANT.error,
      showPulse: false,
    }
  }

  if (status === 'online' && runningJobsCount > 0) {
    return {
      label: AGENT_STATUS_LABELS.online,
      variant: AGENT_STATUS_BADGE_VARIANT.online,
      showPulse: true,
    }
  }

  if (status === 'online' && isOutdated && runningJobsCount === 0) {
    return {
      label: AGENT_OUTDATED_LABEL,
      variant: AGENT_OUTDATED_BADGE_VARIANT,
      showPulse: false,
    }
  }

  if (status === 'online') {
    return {
      label: AGENT_STATUS_LABELS.online,
      variant: AGENT_STATUS_BADGE_VARIANT.online,
      showPulse: true,
    }
  }

  // offline, revoked
  return {
    label: AGENT_STATUS_LABELS[status] || status,
    variant: AGENT_STATUS_BADGE_VARIANT[status] || 'secondary',
    showPulse: false,
  }
}

/**
 * AgentStatusBadge displays the current status of an agent.
 *
 * Status states:
 * - error: Agent reported an error state (red)
 * - online + running jobs: Agent is busy (green with pulse)
 * - online + outdated + idle: Agent needs update (amber/warning)
 * - online: Agent is connected and responsive (green with pulse)
 * - offline: Agent hasn't sent heartbeat recently (gray)
 * - revoked: Agent access has been revoked (outlined)
 */
export function AgentStatusBadge({
  status,
  isOutdated = false,
  runningJobsCount = 0,
  className,
  showLabel = true,
}: AgentStatusBadgeProps) {
  const { label, variant, showPulse } = getEffectiveState(status, isOutdated, runningJobsCount)

  return (
    <Badge
      variant={variant as any}
      className={cn(
        showPulse && 'relative pl-5',
        className
      )}
    >
      {showPulse && (
        <span className="absolute left-1.5 top-1/2 -translate-y-1/2 h-2 w-2 rounded-full bg-green-400 animate-pulse" />
      )}
      {showLabel && label}
    </Badge>
  )
}

export default AgentStatusBadge
