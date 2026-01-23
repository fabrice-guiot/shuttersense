/**
 * Analytics API Types
 *
 * Types for the analytics/storage metrics API endpoints.
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

// ============================================================================
// Storage Metrics Types
// ============================================================================

/** Storage metrics response from API */
export interface StorageStatsResponse {
  // Cumulative counters from StorageMetrics table
  total_reports_generated: number
  completed_jobs_purged: number
  failed_jobs_purged: number
  completed_results_purged_original: number
  completed_results_purged_copy: number
  estimated_bytes_purged: number

  // Real-time statistics (computed from current data)
  total_results_retained: number
  original_results_retained: number
  copy_results_retained: number
  preserved_results_count: number
  reports_retained_json_bytes: number
  reports_retained_html_bytes: number

  // Derived metrics
  deduplication_ratio: number
  storage_savings_bytes: number
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format bytes for display (human-readable)
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`
}

/**
 * Format percentage for display
 */
export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}

/**
 * Calculate total storage used
 */
export function getTotalStorageUsed(stats: StorageStatsResponse): number {
  return stats.reports_retained_json_bytes + stats.reports_retained_html_bytes
}

/**
 * Calculate total results purged
 */
export function getTotalResultsPurged(stats: StorageStatsResponse): number {
  return stats.completed_results_purged_original + stats.completed_results_purged_copy
}
