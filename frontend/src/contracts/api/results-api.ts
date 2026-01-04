/**
 * Results API Contracts
 *
 * Defines TypeScript interfaces for analysis result endpoints.
 * These contracts mirror the backend FastAPI endpoints for Phase 4 implementation.
 */

// ============================================================================
// Entity Types
// ============================================================================

export type ResultStatus = 'COMPLETED' | 'FAILED' | 'CANCELLED'

export type ToolType = 'photostats' | 'photo_pairing' | 'pipeline_validation'

export type SortField = 'created_at' | 'duration_seconds' | 'files_scanned'

export type SortOrder = 'asc' | 'desc'

// ============================================================================
// Tool-Specific Results
// ============================================================================

export interface PhotoStatsResults {
  /** Total size in bytes */
  total_size: number
  /** Total file count */
  total_files: number
  /** File counts by extension */
  file_counts: Record<string, number>
  /** List of orphaned image files */
  orphaned_images: string[]
  /** List of orphaned XMP files */
  orphaned_xmp: string[]
}

export interface CameraUsageInfo {
  /** Camera display name */
  name: string
  /** Camera serial number */
  serial_number?: string
  /** Number of images for this camera */
  image_count: number
  /** Number of groups for this camera */
  group_count: number
}

export interface PhotoPairingResults {
  /** Number of image groups */
  group_count: number
  /** Total images in groups */
  image_count: number
  /** Camera usage details by camera ID */
  camera_usage: Record<string, CameraUsageInfo | number>
}

export interface PipelineValidationResults {
  /** Counts by consistency status */
  consistency_counts: {
    CONSISTENT: number
    PARTIAL: number
    INCONSISTENT: number
  }
}

export type ToolResults = PhotoStatsResults | PhotoPairingResults | PipelineValidationResults

// ============================================================================
// API Response Types
// ============================================================================

export interface AnalysisResultSummary {
  id: number
  collection_id: number
  collection_name: string
  tool: ToolType
  status: ResultStatus
  started_at: string // ISO 8601 timestamp
  completed_at: string // ISO 8601 timestamp
  duration_seconds: number
  files_scanned: number | null
  issues_found: number | null
  has_report: boolean
}

export interface AnalysisResult {
  id: number
  collection_id: number
  collection_name: string
  tool: ToolType
  pipeline_id: number | null
  pipeline_name: string | null
  status: ResultStatus
  started_at: string // ISO 8601 timestamp
  completed_at: string // ISO 8601 timestamp
  duration_seconds: number
  files_scanned: number | null
  issues_found: number | null
  error_message: string | null
  has_report: boolean
  results: ToolResults
  created_at: string // ISO 8601 timestamp
}

export interface ResultListResponse {
  items: AnalysisResultSummary[]
  total: number
  limit: number
  offset: number
}

export interface ResultDetailResponse {
  result: AnalysisResult
}

export interface ResultStatsResponse {
  /** Total number of results */
  total_results: number
  /** Number of completed results */
  completed_count: number
  /** Number of failed results */
  failed_count: number
  /** Count by tool type */
  by_tool: Record<ToolType, number>
  /** Last run timestamp */
  last_run: string | null // ISO 8601 timestamp
}

export interface ResultDeleteResponse {
  message: string
  deleted_id: number
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface ResultListQueryParams {
  /** Filter by collection */
  collection_id?: number
  /** Filter by tool type */
  tool?: ToolType
  /** Filter by status */
  status?: ResultStatus
  /** Filter by date range (from) */
  from_date?: string // YYYY-MM-DD
  /** Filter by date range (to) */
  to_date?: string // YYYY-MM-DD
  /** Maximum results to return */
  limit?: number
  /** Number of results to skip */
  offset?: number
  /** Field to sort by */
  sort_by?: SortField
  /** Sort order */
  sort_order?: SortOrder
}

// ============================================================================
// API Error Response
// ============================================================================

export interface ResultsErrorResponse {
  detail: string
  userMessage?: string
}

// ============================================================================
// Frontend-Specific Types
// ============================================================================

/**
 * Filter state used in frontend UI
 * 'ALL' is a UI-only value, not sent to backend
 */
export interface ResultFilters {
  collection_id: number | null
  tool: ToolType | 'ALL' | ''
  status: ResultStatus | 'ALL' | ''
  from_date: string
  to_date: string
}

/**
 * Convert frontend filters to API query params
 */
export function toApiQueryParams(filters: ResultFilters): ResultListQueryParams {
  const params: ResultListQueryParams = {}

  if (filters.collection_id) {
    params.collection_id = filters.collection_id
  }

  if (filters.tool && filters.tool !== 'ALL') {
    params.tool = filters.tool as ToolType
  }

  if (filters.status && filters.status !== 'ALL') {
    params.status = filters.status as ResultStatus
  }

  if (filters.from_date) {
    params.from_date = filters.from_date
  }

  if (filters.to_date) {
    params.to_date = filters.to_date
  }

  return params
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/results
 *
 * List analysis results with optional filters
 *
 * Query Parameters: ResultListQueryParams
 *
 * Response: 200 ResultListResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/results/{result_id}
 *
 * Get analysis result details
 *
 * Path Parameters:
 *   - result_id: number
 *
 * Response: 200 AnalysisResult
 * Errors:
 *   - 404: Result not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/results/{result_id}
 *
 * Delete an analysis result
 *
 * Path Parameters:
 *   - result_id: number
 *
 * Response: 200 ResultDeleteResponse
 * Errors:
 *   - 404: Result not found
 *   - 500: Internal server error
 */

/**
 * GET /api/results/{result_id}/report
 *
 * Download HTML report
 *
 * Path Parameters:
 *   - result_id: number
 *
 * Response: 200 HTML file with Content-Disposition header
 * Errors:
 *   - 404: Result or report not found
 *   - 500: Internal server error
 */

/**
 * GET /api/results/stats
 *
 * Get results statistics for KPIs
 *
 * Response: 200 ResultStatsResponse
 */
