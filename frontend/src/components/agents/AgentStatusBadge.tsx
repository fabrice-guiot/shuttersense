/**
 * AgentStatusBadge Component
 *
 * Displays agent status with appropriate styling for each state.
 * Supports derived states beyond the base API status.
 *
 * Individual agent progression (lowest → highest):
 *   Offline > Unverified > Idle > Outdated > Running
 *
 * An unverified agent cannot progress beyond Unverified (except in dev mode).
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Issue #242 - Outdated Agent Detection
 * Issue #236 - Continuous Attestation
 */

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AgentStatus } from '@/contracts/api/agent-api'
import {
  AGENT_STATUS_LABELS,
  AGENT_STATUS_BADGE_VARIANT,
  AGENT_OUTDATED_LABEL,
  AGENT_OUTDATED_BADGE_VARIANT,
  AGENT_UNVERIFIED_LABEL,
  AGENT_UNVERIFIED_BADGE_VARIANT,
  AGENT_IDLE_LABEL,
  AGENT_RUNNING_LABEL,
} from '@/contracts/domain-labels'

interface AgentStatusBadgeProps {
  status: AgentStatus
  isOutdated?: boolean
  isVerified?: boolean
  runningJobsCount?: number
  /** True when the agent has no platform set (pre-upgrade build) */
  hasMissingPlatform?: boolean
  className?: string
  showLabel?: boolean
}

/**
 * Determine the effective display state for the badge.
 *
 * Progression: Offline > Unverified > Idle > Outdated > Running
 * Error and Revoked are terminal states shown unconditionally.
 */
function getEffectiveState(
  status: AgentStatus,
  isOutdated: boolean,
  isVerified: boolean,
  runningJobsCount: number,
  hasMissingPlatform: boolean
): { label: string; variant: string; showPulse: boolean } {
  // Terminal states — always shown as-is
  if (status === 'error') {
    return {
      label: AGENT_STATUS_LABELS.error,
      variant: AGENT_STATUS_BADGE_VARIANT.error,
      showPulse: false,
    }
  }

  if (status === 'revoked') {
    return {
      label: AGENT_STATUS_LABELS.revoked,
      variant: AGENT_STATUS_BADGE_VARIANT.revoked,
      showPulse: false,
    }
  }

  if (status === 'offline') {
    return {
      label: AGENT_STATUS_LABELS.offline,
      variant: AGENT_STATUS_BADGE_VARIANT.offline,
      showPulse: false,
    }
  }

  // --- Agent is online from here ---

  // Unverified: agent cannot progress further (blocked from jobs)
  if (!isVerified) {
    return {
      label: AGENT_UNVERIFIED_LABEL,
      variant: AGENT_UNVERIFIED_BADGE_VARIANT,
      showPulse: false,
    }
  }

  // Running: online + verified + active jobs (highest progression)
  if (runningJobsCount > 0) {
    return {
      label: AGENT_RUNNING_LABEL,
      variant: AGENT_STATUS_BADGE_VARIANT.online,
      showPulse: true,
    }
  }

  // Outdated: online + verified + idle + outdated manifest
  if (isOutdated || hasMissingPlatform) {
    return {
      label: AGENT_OUTDATED_LABEL,
      variant: AGENT_OUTDATED_BADGE_VARIANT,
      showPulse: false,
    }
  }

  // Idle: online + verified + no jobs + up to date
  return {
    label: AGENT_IDLE_LABEL,
    variant: AGENT_STATUS_BADGE_VARIANT.online,
    showPulse: true,
  }
}

/**
 * AgentStatusBadge displays the current status of an agent.
 *
 * Status states (progression):
 * - offline: Agent hasn't sent heartbeat recently (gray)
 * - unverified: Binary checksum doesn't match any release manifest (red)
 * - idle: Agent is online, verified, no active jobs (green with pulse)
 * - outdated: Agent is idle but running an old version (amber/warning)
 * - running: Agent is executing jobs (green with pulse)
 *
 * Terminal states:
 * - error: Agent reported an error state (red)
 * - revoked: Agent access has been revoked (outlined)
 */
export function AgentStatusBadge({
  status,
  isOutdated = false,
  isVerified = true,
  runningJobsCount = 0,
  hasMissingPlatform = false,
  className,
  showLabel = true,
}: AgentStatusBadgeProps) {
  const { label, variant, showPulse } = getEffectiveState(status, isOutdated, isVerified, runningJobsCount, hasMissingPlatform)

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
