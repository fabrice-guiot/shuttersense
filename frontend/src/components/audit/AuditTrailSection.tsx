/**
 * AuditTrailSection Component
 *
 * Renders a border-separated section showing created/modified timestamps
 * and user attribution. Used in detail dialogs and detail pages.
 *
 * Issue #120: Audit Trail Visibility Enhancement (Phase 4)
 */

import { formatDateTime } from '@/utils/dateFormat'
import type { AuditInfo, AuditUserSummary } from '@/contracts/api/audit-api'

// ============================================================================
// Props
// ============================================================================

export interface AuditTrailSectionProps {
  /** Structured audit trail from the API response. */
  audit?: AuditInfo | null
}

// ============================================================================
// Helpers
// ============================================================================

function formatUser(user: AuditUserSummary | null): string {
  if (!user) return '\u2014'
  return user.display_name || user.email || '\u2014'
}

// ============================================================================
// Component
// ============================================================================

export function AuditTrailSection({ audit }: AuditTrailSectionProps) {
  if (!audit) return null

  const showModified = audit.created_at !== audit.updated_at

  return (
    <div className="border-t pt-4 mt-4 space-y-2 text-sm">
      <div className="flex items-baseline justify-between">
        <span className="text-muted-foreground">Created</span>
        <div className="text-right">
          <div>{formatDateTime(audit.created_at)}</div>
          <div className="text-xs text-muted-foreground">
            {formatUser(audit.created_by)}
          </div>
        </div>
      </div>
      {showModified && (
        <div className="flex items-baseline justify-between">
          <span className="text-muted-foreground">Modified</span>
          <div className="text-right">
            <div>{formatDateTime(audit.updated_at)}</div>
            <div className="text-xs text-muted-foreground">
              {formatUser(audit.updated_by)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
