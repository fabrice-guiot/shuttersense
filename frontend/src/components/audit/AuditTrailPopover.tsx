/**
 * AuditTrailPopover Component
 *
 * Displays a relative timestamp with a hover popover showing full audit details
 * (created/modified by whom, when). Used in list view "Modified" columns.
 *
 * Issue #120: Audit Trail Visibility Enhancement (Phase 4)
 */

import { useState, useRef, useCallback } from 'react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { formatRelativeTime, formatDateTime } from '@/utils/dateFormat'
import type { AuditInfo, AuditUserSummary } from '@/contracts/api/audit-api'

// ============================================================================
// Props
// ============================================================================

export interface AuditTrailPopoverProps {
  /** Structured audit trail from the API response. */
  audit?: AuditInfo | null
  /** Fallback timestamp when audit is not available (e.g., legacy records). */
  fallbackTimestamp?: string | null
}

// ============================================================================
// Helpers
// ============================================================================

const CLOSE_DELAY_MS = 150

function formatUser(user: AuditUserSummary | null): string {
  if (!user) return '\u2014'
  return user.display_name || user.email || '\u2014'
}

// ============================================================================
// Component
// ============================================================================

export function AuditTrailPopover({
  audit,
  fallbackTimestamp,
}: AuditTrailPopoverProps) {
  const [open, setOpen] = useState(false)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }, [])

  const scheduleClose = useCallback(() => {
    clearCloseTimer()
    closeTimerRef.current = setTimeout(() => setOpen(false), CLOSE_DELAY_MS)
  }, [clearCloseTimer])

  const handleMouseEnter = useCallback(() => {
    clearCloseTimer()
    setOpen(true)
  }, [clearCloseTimer])

  const handleMouseLeave = useCallback(() => {
    scheduleClose()
  }, [scheduleClose])

  // Case 1: Full audit data available — show popover
  if (audit) {
    const showModified = audit.created_at !== audit.updated_at

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <span
            className="cursor-default border-b border-dotted border-muted-foreground/50"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            {formatRelativeTime(audit.updated_at)}
          </span>
        </PopoverTrigger>
        <PopoverContent
          className="w-64 p-3 text-sm"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="space-y-2">
            <div>
              <div className="text-xs font-medium text-muted-foreground">
                Created
              </div>
              <div>{formatDateTime(audit.created_at)}</div>
              <div className="text-xs text-muted-foreground">
                {formatUser(audit.created_by)}
              </div>
            </div>
            {showModified && (
              <div>
                <div className="text-xs font-medium text-muted-foreground">
                  Modified
                </div>
                <div>{formatDateTime(audit.updated_at)}</div>
                <div className="text-xs text-muted-foreground">
                  {formatUser(audit.updated_by)}
                </div>
              </div>
            )}
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  // Case 2: No audit but fallback timestamp — plain text
  if (fallbackTimestamp) {
    return <span>{formatRelativeTime(fallbackTimestamp)}</span>
  }

  // Case 3: Nothing available
  return <span>{'\u2014'}</span>
}
