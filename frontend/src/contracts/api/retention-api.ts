/**
 * Retention Configuration API Contracts
 *
 * Issue #92: Storage Optimization for Analysis Results
 * Defines TypeScript interfaces for retention configuration endpoints.
 */

// ============================================================================
// Type Definitions
// ============================================================================

/** Valid retention period options (days, 0 = unlimited) */
export type RetentionDays = 0 | 1 | 2 | 5 | 7 | 14 | 30 | 90 | 180 | 365

/** Valid preserve count options */
export type PreserveCount = 1 | 2 | 3 | 5 | 10

// ============================================================================
// Response Schemas
// ============================================================================

/** Retention settings response from API */
export interface RetentionSettingsResponse {
  /** Days to retain completed jobs (0 = unlimited) */
  job_completed_days: number
  /** Days to retain failed jobs (0 = unlimited) */
  job_failed_days: number
  /** Days to retain completed results (0 = unlimited) */
  result_completed_days: number
  /** Minimum results to keep per (collection, tool) combination */
  preserve_per_collection: number
}

/** Retention settings update request */
export interface RetentionSettingsUpdate {
  /** Days to retain completed jobs (0 = unlimited) */
  job_completed_days?: RetentionDays
  /** Days to retain failed jobs (0 = unlimited) */
  job_failed_days?: RetentionDays
  /** Days to retain completed results (0 = unlimited) */
  result_completed_days?: RetentionDays
  /** Minimum results to keep per (collection, tool) combination */
  preserve_per_collection?: PreserveCount
}

// ============================================================================
// Constants
// ============================================================================

/** Display labels for retention period values */
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
  365: '365 days',
}

/** Display labels for preserve count values */
export const PRESERVE_LABELS: Record<PreserveCount, string> = {
  1: '1 result',
  2: '2 results',
  3: '3 results',
  5: '5 results',
  10: '10 results',
}

/** Valid retention day values */
export const VALID_RETENTION_DAYS: RetentionDays[] = [0, 1, 2, 5, 7, 14, 30, 90, 180, 365]

/** Valid preserve count values */
export const VALID_PRESERVE_COUNTS: PreserveCount[] = [1, 2, 3, 5, 10]

/** Default retention values */
export const DEFAULT_RETENTION: RetentionSettingsResponse = {
  job_completed_days: 2,
  job_failed_days: 7,
  result_completed_days: 0,
  preserve_per_collection: 1,
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

/**
 * Check if a value is a valid retention days option
 */
export function isValidRetentionDays(value: number): value is RetentionDays {
  return VALID_RETENTION_DAYS.indexOf(value as RetentionDays) !== -1
}

/**
 * Check if a value is a valid preserve count option
 */
export function isValidPreserveCount(value: number): value is PreserveCount {
  return VALID_PRESERVE_COUNTS.indexOf(value as PreserveCount) !== -1
}

// ============================================================================
// API Endpoint Definitions
// ============================================================================

/**
 * GET /api/config/retention
 *
 * Get current retention settings for the authenticated user's team.
 * Returns default values if settings have not been configured.
 *
 * Response: 200 RetentionSettingsResponse
 * Errors:
 *   - 401: Unauthorized
 */

/**
 * PUT /api/config/retention
 *
 * Update retention settings for the authenticated user's team.
 * All fields are optional; only provided fields are updated.
 *
 * Request Body: RetentionSettingsUpdate
 *
 * Response: 200 RetentionSettingsResponse
 * Errors:
 *   - 400: Invalid retention value
 *   - 401: Unauthorized
 */
