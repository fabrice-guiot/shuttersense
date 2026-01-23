/**
 * Retention API Types
 *
 * Types for the retention configuration API endpoints.
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

// ============================================================================
// Retention Period Types
// ============================================================================

/** Valid retention period options (days, 0 = unlimited) */
export type RetentionDays = 0 | 1 | 2 | 5 | 7 | 14 | 30 | 90 | 180 | 365

/** Valid preserve count options */
export type PreserveCount = 1 | 2 | 3 | 5 | 10

// ============================================================================
// API Response/Request Types
// ============================================================================

/** Retention settings response from API */
export interface RetentionSettingsResponse {
  job_completed_days: number
  job_failed_days: number
  result_completed_days: number
  preserve_per_collection: number
}

/** Retention settings update request (all fields optional) */
export interface RetentionSettingsUpdate {
  job_completed_days?: RetentionDays
  job_failed_days?: RetentionDays
  result_completed_days?: RetentionDays
  preserve_per_collection?: PreserveCount
}

// ============================================================================
// Display Labels
// ============================================================================

/** Display label for retention period */
export const RETENTION_LABELS: Record<RetentionDays, string> = {
  0: 'Unlimited',
  1: '1 day',
  2: '2 days',
  5: '5 days',
  7: '7 days',
  14: '14 days',
  30: '30 days',
  90: '90 days',
  180: '180 days',
  365: '365 days'
}

/** Display label for preserve count */
export const PRESERVE_LABELS: Record<PreserveCount, string> = {
  1: '1 result',
  2: '2 results',
  3: '3 results',
  5: '5 results',
  10: '10 results'
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format retention days for display
 */
export function formatRetentionDays(days: number): string {
  if (days === 0) return 'Unlimited'
  if (days === 1) return '1 day'
  return `${days} days`
}

/**
 * Format preserve count for display
 */
export function formatPreserveCount(count: number): string {
  if (count === 1) return '1 result'
  return `${count} results`
}
