/**
 * Audit trail API types.
 *
 * Shared types for audit user attribution displayed in list view popovers
 * and detail dialog sections. Matches backend AuditUserSummary and AuditInfo
 * Pydantic schemas.
 *
 * Issue #120: Audit Trail Visibility Enhancement
 */

/** Minimal user representation for audit attribution display. */
export interface AuditUserSummary {
  /** User GUID (usr_xxx format) — never the internal numeric ID. */
  guid: string
  /** Human-readable name. May be null for system users. */
  display_name: string | null
  /** User email address. */
  email: string
}

/** Structured audit trail included in entity API responses. */
export interface AuditInfo {
  /** Record creation timestamp (ISO 8601). */
  created_at: string
  /** User who created the record. Null for historical records or deleted users. */
  created_by: AuditUserSummary | null
  /** Last modification timestamp (ISO 8601). */
  updated_at: string
  /** User who last modified the record. Null for historical records or deleted users. */
  updated_by: AuditUserSummary | null
}
