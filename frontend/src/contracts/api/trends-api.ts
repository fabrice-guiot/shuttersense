/**
 * Trends API Contracts
 *
 * Defines TypeScript interfaces for trend analysis endpoints.
 * These contracts mirror the backend FastAPI endpoints for Phase 6 implementation.
 */

// ============================================================================
// Entity Types
// ============================================================================

export type TrendDirection = 'improving' | 'stable' | 'degrading' | 'insufficient_data'

// ============================================================================
// PhotoStats Trend Types
// ============================================================================

/** Single data point for PhotoStats comparison mode */
export interface PhotoStatsTrendPoint {
  /** Timestamp of the analysis run */
  date: string // ISO 8601 timestamp
  /** ID of the analysis result */
  result_id: number
  /** Count of orphaned image files */
  orphaned_images_count: number
  /** Count of orphaned XMP files */
  orphaned_xmp_count: number
  /** Total files in collection at this point */
  total_files: number
  /** Total size in bytes at this point */
  total_size: number
}

export interface PhotoStatsCollectionTrend {
  collection_id: number
  collection_name: string
  data_points: PhotoStatsTrendPoint[]
}

/** Aggregated data point for PhotoStats (summed across all collections) */
export interface PhotoStatsAggregatedPoint {
  date: string // ISO 8601 timestamp
  /** Total orphaned images across all collections */
  orphaned_images: number
  /** Total orphaned metadata files (XMP) across all collections */
  orphaned_metadata: number
  /** Number of collections with data for this date */
  collections_included: number
}

/**
 * PhotoStats trend response.
 * - aggregated mode: data_points contains aggregated data
 * - comparison mode: collections contains per-collection data
 */
export interface PhotoStatsTrendResponse {
  mode: 'aggregated' | 'comparison'
  /** Aggregated trend data (used in aggregated mode) */
  data_points: PhotoStatsAggregatedPoint[]
  /** Per-collection trend data (used in comparison mode) */
  collections: PhotoStatsCollectionTrend[]
}

// ============================================================================
// Photo Pairing Trend Types
// ============================================================================

/** Single data point for Photo Pairing comparison mode */
export interface PhotoPairingTrendPoint {
  /** Timestamp of the analysis run */
  date: string // ISO 8601 timestamp
  /** ID of the analysis result */
  result_id: number
  /** Number of image groups */
  group_count: number
  /** Total images in groups */
  image_count: number
  /** Map of camera_id to image count */
  camera_usage: Record<string, number>
}

export interface PhotoPairingCollectionTrend {
  collection_id: number
  collection_name: string
  /** List of camera IDs found across all data points */
  cameras: string[]
  data_points: PhotoPairingTrendPoint[]
}

/** Aggregated data point for Photo Pairing (summed across all collections) */
export interface PhotoPairingAggregatedPoint {
  date: string // ISO 8601 timestamp
  /** Total image groups across all collections */
  group_count: number
  /** Total images across all collections */
  image_count: number
  /** Number of collections with data for this date */
  collections_included: number
}

/**
 * Photo Pairing trend response.
 * - aggregated mode: data_points contains aggregated data (no camera breakdown)
 * - comparison mode: collections contains per-collection data with cameras
 */
export interface PhotoPairingTrendResponse {
  mode: 'aggregated' | 'comparison'
  /** Aggregated trend data (used in aggregated mode) */
  data_points: PhotoPairingAggregatedPoint[]
  /** Per-collection trend data (used in comparison mode) */
  collections: PhotoPairingCollectionTrend[]
}

// ============================================================================
// Pipeline Validation Trend Types
// ============================================================================

/** Single data point for Pipeline Validation comparison mode */
export interface PipelineValidationTrendPoint {
  /** Timestamp of the analysis run */
  date: string // ISO 8601 timestamp
  /** ID of the analysis result */
  result_id: number
  /** Pipeline used for validation */
  pipeline_id: number
  /** Pipeline name */
  pipeline_name: string
  /** Count of CONSISTENT status */
  consistent_count: number
  /** Count of PARTIAL status */
  partial_count: number
  /** Count of INCONSISTENT status */
  inconsistent_count: number
  /** Percentage of CONSISTENT status (0-100) */
  consistent_ratio: number
  /** Percentage of PARTIAL status (0-100) */
  partial_ratio: number
  /** Percentage of INCONSISTENT status (0-100) */
  inconsistent_ratio: number
}

export interface PipelineValidationCollectionTrend {
  collection_id: number
  collection_name: string
  data_points: PipelineValidationTrendPoint[]
}

/**
 * Aggregated data point for Pipeline Validation (recalculated from summed counts).
 *
 * Series:
 * - overall_consistency_pct: Total CONSISTENT / Total images
 * - black_box_consistency_pct: CONSISTENT in Black Box Archive / Total Black Box
 * - browsable_consistency_pct: CONSISTENT in Browsable Archive / Total Browsable
 * - overall_inconsistent_pct: Total INCONSISTENT / Total images
 */
export interface PipelineValidationAggregatedPoint {
  date: string // ISO 8601 timestamp
  /** Overall consistency % across all collections */
  overall_consistency_pct: number
  /** Overall inconsistent % across all collections */
  overall_inconsistent_pct: number
  /** Consistency % for Black Box Archive termination */
  black_box_consistency_pct: number
  /** Consistency % for Browsable Archive termination */
  browsable_consistency_pct: number
  /** Total images validated */
  total_images: number
  /** Total CONSISTENT count */
  consistent_count: number
  /** Total INCONSISTENT count */
  inconsistent_count: number
  /** Number of collections with data for this date */
  collections_included: number
}

/**
 * Pipeline Validation trend response.
 * - aggregated mode: data_points contains aggregated data with percentages
 * - comparison mode: collections contains per-collection data
 */
export interface PipelineValidationTrendResponse {
  mode: 'aggregated' | 'comparison'
  /** Aggregated trend data (used in aggregated mode) */
  data_points: PipelineValidationAggregatedPoint[]
  /** Per-collection trend data (used in comparison mode) */
  collections: PipelineValidationCollectionTrend[]
}

// ============================================================================
// Display Graph Trend Types
// ============================================================================

/**
 * Aggregated display graph trend data point.
 * Data is aggregated across all pipelines for each date.
 */
export interface DisplayGraphTrendPoint {
  /** Timestamp (aggregated by date) */
  date: string // ISO 8601 timestamp
  /** Total paths enumerated across all pipelines */
  total_paths: number
  /** Valid paths (completed on real termination nodes, not truncated) */
  valid_paths: number
  /** Paths ending in Black Box Archive termination */
  black_box_archive_paths: number
  /** Paths ending in Browsable Archive termination */
  browsable_archive_paths: number
}

export interface DisplayGraphTrendResponse {
  /** Aggregated data points across all pipelines */
  data_points: DisplayGraphTrendPoint[]
  /** List of pipelines included in the aggregation */
  pipelines_included: Array<{
    pipeline_id: number
    pipeline_name: string
    result_count: number
  }>
}

// ============================================================================
// Trend Summary Types
// ============================================================================

export interface TrendSummaryResponse {
  /** Collection ID (null for all collections) */
  collection_id: number | null
  /** Trend direction for orphaned files */
  orphaned_trend: TrendDirection
  /** Trend direction for consistency */
  consistency_trend: TrendDirection
  /** Last PhotoStats run timestamp */
  last_photostats: string | null // ISO 8601 timestamp
  /** Last Photo Pairing run timestamp */
  last_photo_pairing: string | null // ISO 8601 timestamp
  /** Last Pipeline Validation run timestamp */
  last_pipeline_validation: string | null // ISO 8601 timestamp
  /** Number of data points available by tool */
  data_points_available: {
    photostats: number
    photo_pairing: number
    pipeline_validation: number
  }
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface TrendQueryParams {
  /** Comma-separated collection IDs */
  collection_ids?: string
  /** Filter by date range (from) */
  from_date?: string // YYYY-MM-DD
  /** Filter by date range (to) */
  to_date?: string // YYYY-MM-DD
  /** Maximum data points per collection */
  limit?: number
}

export interface PipelineValidationTrendQueryParams extends TrendQueryParams {
  /** Filter by pipeline ID */
  pipeline_id?: number
  /** Filter by pipeline version */
  pipeline_version?: number
}

export interface TrendSummaryQueryParams {
  /** Collection ID (optional, for single collection) */
  collection_id?: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface TrendsErrorResponse {
  detail: string
  userMessage?: string
}

// ============================================================================
// Frontend-Specific Types
// ============================================================================

/**
 * Filter state used in frontend UI
 */
export interface TrendFilters {
  collection_ids: number[]
  from_date: string
  to_date: string
  limit: number
}

/**
 * Date range presets for trend filtering
 */
export type DateRangePreset = 'last_7_days' | 'last_30_days' | 'last_90_days' | 'last_year' | 'all_time'

/**
 * Get date range from preset
 */
export function getDateRangeFromPreset(preset: DateRangePreset): { from_date: string; to_date: string } {
  const now = new Date()
  const to_date = now.toISOString().split('T')[0]
  let from_date: string

  switch (preset) {
    case 'last_7_days':
      from_date = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      break
    case 'last_30_days':
      from_date = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      break
    case 'last_90_days':
      from_date = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      break
    case 'last_year':
      from_date = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      break
    case 'all_time':
    default:
      from_date = ''
  }

  return { from_date, to_date }
}

/**
 * Convert frontend filters to API query params
 */
export function toApiQueryParams(filters: TrendFilters): TrendQueryParams {
  const params: TrendQueryParams = {}

  if (filters.collection_ids.length > 0) {
    params.collection_ids = filters.collection_ids.join(',')
  }

  if (filters.from_date) {
    params.from_date = filters.from_date
  }

  if (filters.to_date) {
    params.to_date = filters.to_date
  }

  if (filters.limit && filters.limit !== 50) {
    params.limit = filters.limit
  }

  return params
}

// ============================================================================
// Chart Data Types (for Recharts integration)
// ============================================================================

/**
 * Normalized chart data point for PhotoStats trends
 */
export interface PhotoStatsChartData {
  date: string
  orphaned_images: number
  orphaned_xmp: number
  total_files: number
}

/**
 * Normalized chart data point for Photo Pairing trends
 * Includes dynamic camera_id fields
 */
export interface PhotoPairingChartData {
  date: string
  group_count: number
  image_count: number
  [cameraId: string]: string | number // Dynamic camera usage fields
}

/**
 * Normalized chart data point for Pipeline Validation trends
 */
export interface PipelineValidationChartData {
  date: string
  consistent: number
  partial: number
  inconsistent: number
  consistent_ratio: number
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/trends/photostats
 *
 * Get PhotoStats trends (orphaned files over time)
 *
 * Query Parameters: TrendQueryParams
 *
 * Response: 200 PhotoStatsTrendResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/trends/photo-pairing
 *
 * Get Photo Pairing trends (camera usage over time)
 *
 * Query Parameters: TrendQueryParams
 *
 * Response: 200 PhotoPairingTrendResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/trends/pipeline-validation
 *
 * Get Pipeline Validation trends (consistency over time)
 *
 * Query Parameters: PipelineValidationTrendQueryParams
 *
 * Response: 200 PipelineValidationTrendResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/trends/summary
 *
 * Get trend summary for dashboard
 *
 * Query Parameters: TrendSummaryQueryParams
 *
 * Response: 200 TrendSummaryResponse
 * Errors:
 *   - 500: Internal server error
 */
