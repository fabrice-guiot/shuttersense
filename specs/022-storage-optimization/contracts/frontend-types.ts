/**
 * Frontend TypeScript Types: Storage Optimization
 * Feature: 022-storage-optimization
 * Date: 2026-01-22
 *
 * These types should be added to frontend/src/contracts/api/
 */

// =============================================================================
// Retention Configuration Types
// File: frontend/src/contracts/api/retention-api.ts
// =============================================================================

/** Valid retention period options (days, 0 = unlimited) */
export type RetentionDays = 0 | 1 | 2 | 5 | 7 | 14 | 30 | 90 | 180 | 365

/** Valid preserve count options */
export type PreserveCount = 1 | 2 | 3 | 5 | 10

/** Retention settings response from API */
export interface RetentionSettingsResponse {
  job_completed_days: number
  job_failed_days: number
  result_completed_days: number
  preserve_per_collection: number
}

/** Retention settings update request */
export interface RetentionSettingsUpdate {
  job_completed_days?: RetentionDays
  job_failed_days?: RetentionDays
  result_completed_days?: RetentionDays
  preserve_per_collection?: PreserveCount
}

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
  365: '365 days',
}

/** Display label for preserve count */
export const PRESERVE_LABELS: Record<PreserveCount, string> = {
  1: '1 result',
  2: '2 results',
  3: '3 results',
  5: '5 results',
  10: '10 results',
}

// =============================================================================
// Extended Result Types
// File: Add to frontend/src/contracts/api/results-api.ts
// =============================================================================

/** Extended result status including NO_CHANGE */
export type ResultStatus = 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'NO_CHANGE'

/** Extended result summary with storage optimization fields */
export interface AnalysisResultSummary {
  guid: string
  collection_guid: string | null
  collection_name: string | null
  tool: string
  pipeline_guid: string | null
  pipeline_version: number | null
  pipeline_name: string | null
  status: ResultStatus
  started_at: string
  completed_at: string
  duration_seconds: number
  files_scanned: number | null
  issues_found: number | null
  has_report: boolean
  /** True if this result references a previous result (no new data) */
  no_change_copy: boolean
  /** SHA-256 hash of Input State (null for legacy results) */
  input_state_hash: string | null
}

/** Extended result detail response */
export interface AnalysisResultResponse extends AnalysisResultSummary {
  error_message: string | null
  results: Record<string, unknown>
  created_at: string
  /** GUID of source result containing actual report (for NO_CHANGE results) */
  download_report_from: string | null
  /** Whether source result still exists (for NO_CHANGE results) */
  source_result_exists: boolean | null
}

// =============================================================================
// Helper Functions
// File: frontend/src/utils/retention.ts
// =============================================================================

/**
 * Format retention days for display
 */
export function formatRetentionDays(days: number): string {
  if (days === 0) return 'Unlimited'
  if (days === 1) return '1 day'
  return `${days} days`
}

/**
 * Get status badge variant for result status
 */
export function getResultStatusVariant(
  status: ResultStatus
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'COMPLETED':
      return 'default'
    case 'NO_CHANGE':
      return 'secondary'
    case 'FAILED':
      return 'destructive'
    case 'CANCELLED':
      return 'outline'
  }
}

/**
 * Get display text for result status
 */
export function getResultStatusLabel(status: ResultStatus): string {
  switch (status) {
    case 'COMPLETED':
      return 'Completed'
    case 'NO_CHANGE':
      return 'No Change'
    case 'FAILED':
      return 'Failed'
    case 'CANCELLED':
      return 'Cancelled'
  }
}

/**
 * Check if a result can have its report downloaded
 */
export function canDownloadReport(result: AnalysisResultSummary): boolean {
  // Has report if has_report is true (either direct or via reference)
  // For NO_CHANGE results, has_report reflects whether source exists
  return result.has_report
}

// =============================================================================
// Storage Metrics Types
// File: frontend/src/contracts/api/storage-metrics-api.ts
// =============================================================================

/** Storage metrics response from API */
export interface StorageMetricsResponse {
  /** Cumulative count of all job completions (COMPLETED, NO_CHANGE, FAILED) */
  total_reports_generated: number
  /** Current count of retained result records */
  reports_retained_count: number
  /** Current total size of results_json across all retained results (bytes) */
  reports_retained_json_bytes: number
  /** Current total size of report_html across all retained results (bytes) */
  reports_retained_html_bytes: number
  /** Cumulative count of completed job records deleted by cleanup */
  completed_jobs_purged: number
  /** Cumulative count of failed job records deleted by cleanup */
  failed_jobs_purged: number
  /** Cumulative count of original results purged (no_change_copy=false) */
  completed_results_purged_original: number
  /** Cumulative count of copy results purged (no_change_copy=true) */
  completed_results_purged_copy: number
  /** Cumulative estimated bytes freed from database (JSON + HTML sizes) */
  estimated_bytes_purged: number
  /** Count of results protected by preserve_per_collection setting */
  preserved_results_count: number
}

/**
 * Format bytes for display (human-readable)
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * Format large numbers with comma separators
 */
export function formatCount(count: number): string {
  return count.toLocaleString()
}
