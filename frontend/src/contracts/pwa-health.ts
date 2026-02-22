/**
 * PWA Health Diagnostics Type Definitions
 *
 * Types for the PWA diagnostics panel that checks installation,
 * service worker, cache, push notifications, and platform issues.
 *
 * Issue #025 - PWA Health Diagnostics
 */

/**
 * Status of an individual diagnostic check.
 */
export type DiagnosticStatus = 'pass' | 'warn' | 'fail' | 'unknown'

/**
 * A single diagnostic check result.
 */
export interface DiagnosticCheck {
  /** Unique identifier for this check */
  id: string
  /** Human-readable label */
  label: string
  /** Check result status */
  status: DiagnosticStatus
  /** Short description of what was found */
  message: string
  /** Optional remediation instructions for warn/fail */
  remediation?: string
  /** Optional detailed information (e.g., cache names, version strings) */
  detail?: string
}

/**
 * A group of related diagnostic checks.
 */
export interface DiagnosticSection {
  /** Unique identifier for this section */
  id: string
  /** Section title */
  title: string
  /** Lucide icon name for the section header */
  icon: string
  /** Overall status (worst status of all checks) */
  overallStatus: DiagnosticStatus
  /** Individual checks in this section */
  checks: DiagnosticCheck[]
}

/**
 * Complete PWA health diagnostics result.
 */
export interface PwaHealthResult {
  /** All diagnostic sections */
  sections: DiagnosticSection[]
  /** When diagnostics were collected (ISO 8601) */
  collectedAt: string
  /** Browser user agent string */
  userAgent: string
  /** Detected browser name */
  browser: string
  /** Detected platform name */
  platform: string
}
