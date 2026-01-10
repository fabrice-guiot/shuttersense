/**
 * Collection API Contracts
 *
 * Defines TypeScript interfaces for all collection-related API endpoints.
 * These contracts mirror the backend FastAPI endpoints (unchanged).
 */

// ============================================================================
// Entity Types
// ============================================================================

export type CollectionType = 'local' | 's3' | 'gcs' | 'smb'
export type CollectionState = 'live' | 'closed' | 'archived'

export interface Collection {
  guid: string  // External identifier (col_xxx) for URL-safe references
  name: string
  type: CollectionType
  state: CollectionState
  location: string
  connector_guid: string | null  // null for LOCAL, required for remote
  pipeline_guid: string | null  // null = use default pipeline at runtime
  pipeline_version: number | null  // pinned version when explicitly assigned
  pipeline_name: string | null  // name of assigned pipeline
  is_accessible: boolean
  accessibility_message: string | null
  cache_ttl: number | null
  created_at: string  // ISO 8601 timestamp
  updated_at: string  // ISO 8601 timestamp
  last_scanned_at: string | null  // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface CollectionCreateRequest {
  name: string
  type: CollectionType
  state: CollectionState
  location: string
  connector_guid: string | null  // null for LOCAL, required for remote
  pipeline_guid?: string | null  // Optional: assign specific pipeline (pip_xxx)
  cache_ttl: number | null
}

export interface CollectionUpdateRequest {
  name?: string
  type?: CollectionType
  state?: CollectionState
  location?: string
  connector_guid?: string | null  // null for LOCAL, required for remote
  pipeline_guid?: string | null  // Optional: update pipeline assignment (pip_xxx)
  cache_ttl?: number | null
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface CollectionListQueryParams {
  state?: CollectionState
  type?: CollectionType
  accessible_only?: boolean
  search?: string  // Case-insensitive partial match on name (Issue #38)
  limit?: number
  offset?: number
}

// ============================================================================
// API Response Types
// ============================================================================

export interface CollectionListResponse {
  collections: Collection[]
  total: number
}

export interface CollectionDetailResponse {
  collection: Collection
}

export interface CollectionTestResponse {
  success: boolean
  message: string
  collection: Collection  // Updated collection with new accessibility status
}

export interface CollectionDeleteResponse {
  success: boolean
  message: string
}

// ============================================================================
// API Error Response
// ============================================================================

export interface CollectionErrorResponse {
  error: {
    message: string
    code?: string
    details?: {
      field?: string
      issue?: string
      [key: string]: unknown
    }
  }
}

// Special error case: Cannot delete collection with results/jobs
export interface CollectionDeleteConflictResponse {
  error: {
    message: string
    code: 'COLLECTION_HAS_DATA'
    details: {
      result_count?: number
      job_count?: number
    }
  }
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/collections
 *
 * List collections with optional filters
 *
 * Query Parameters: CollectionListQueryParams
 *   - state?: 'LIVE' | 'CLOSED' | 'ARCHIVED'
 *   - type?: 'LOCAL' | 'S3' | 'GCS' | 'SMB'
 *   - accessible_only?: boolean
 *   - limit?: number (default: 100)
 *   - offset?: number (default: 0)
 *
 * Response: 200 CollectionListResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * POST /api/collections
 *
 * Create a new collection
 *
 * Request Body: CollectionCreateRequest
 * Validation Rules:
 *   - LOCAL type: connector_guid MUST be null
 *   - Remote types (S3/GCS/SMB): connector_guid MUST be provided (con_xxx format)
 *   - cache_ttl: optional, must be positive integer if provided
 *
 * Response: 201 CollectionDetailResponse
 * Errors:
 *   - 400: Invalid request (validation error)
 *   - 404: Connector not found (for remote types)
 *   - 409: Collection with this name already exists
 *   - 500: Internal server error
 */

/**
 * GET /api/collections/{guid}
 *
 * Get collection by GUID
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 *
 * Response: 200 CollectionDetailResponse
 * Errors:
 *   - 404: Collection not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/collections/{guid}
 *
 * Update existing collection
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 * Request Body: CollectionUpdateRequest
 * Validation Rules: Same as POST /api/collections
 *
 * Response: 200 CollectionDetailResponse
 * Errors:
 *   - 400: Invalid request (validation error)
 *   - 404: Collection or connector not found
 *   - 409: Collection name conflict
 *   - 500: Internal server error
 */

/**
 * DELETE /api/collections/{guid}
 *
 * Delete collection
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 *
 * Response: 200 CollectionDeleteResponse
 * Errors:
 *   - 404: Collection not found
 *   - 409: Collection has results/jobs - CollectionDeleteConflictResponse
 *   - 500: Internal server error
 */

/**
 * POST /api/collections/{guid}/test
 *
 * Test collection accessibility
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 * Request Body: None
 *
 * Response: 200 CollectionTestResponse
 * Errors:
 *   - 404: Collection not found
 *   - 500: Accessibility test failed (CollectionTestResponse with success=false)
 */

// ============================================================================
// Frontend-Specific Types (not in backend API)
// ============================================================================

/**
 * Filter state used in frontend UI
 * 'ALL' is a UI-only value, not sent to backend
 */
export interface CollectionFilters {
  state: CollectionState | 'ALL' | ''
  type: CollectionType | 'ALL' | ''
  accessible_only: boolean
}

/**
 * Convert frontend filters to API query params
 */
export function toApiQueryParams(filters: CollectionFilters): CollectionListQueryParams {
  const params: CollectionListQueryParams = {}

  if (filters.state && filters.state !== 'ALL') {
    params.state = filters.state as CollectionState
  }

  if (filters.type && filters.type !== 'ALL') {
    params.type = filters.type as CollectionType
  }

  if (filters.accessible_only) {
    params.accessible_only = true
  }

  return params
}

// ============================================================================
// KPI Statistics Types (Issue #37)
// ============================================================================

/**
 * Aggregated statistics for all collections (KPI endpoint)
 *
 * GET /api/collections/stats
 *
 * These values are NOT affected by any filter parameters - always shows system-wide totals.
 */
export interface CollectionStatsResponse {
  /** Total number of collections */
  total_collections: number

  /** Total storage used across all collections in bytes */
  storage_used_bytes: number

  /** Human-readable storage amount (e.g., "2.5 TB") */
  storage_used_formatted: string

  /** Total number of files across all collections */
  file_count: number

  /** Total number of images after grouping */
  image_count: number
}

// ============================================================================
// Pipeline Assignment Endpoint Definitions
// ============================================================================

/**
 * POST /api/collections/{guid}/assign-pipeline?pipeline_guid={pipeline_guid}
 *
 * Assign a pipeline to a collection with version pinning
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 * Query Parameters:
 *   - pipeline_guid: string (pipeline GUID to assign, pip_xxx format)
 *
 * The pipeline's current version will be stored as the pinned version.
 * The collection will use this specific version until manually reassigned.
 *
 * Response: 200 Collection (with pipeline_guid, pipeline_version, pipeline_name set)
 * Errors:
 *   - 400: Pipeline is not active
 *   - 404: Collection or pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/collections/{guid}/clear-pipeline
 *
 * Clear pipeline assignment from a collection
 *
 * Path Parameters:
 *   - guid: string (collection GUID, col_xxx format)
 *
 * After clearing, the collection will use the default pipeline at runtime.
 *
 * Response: 200 Collection (with pipeline_guid, pipeline_version, pipeline_name set to null)
 * Errors:
 *   - 404: Collection not found
 *   - 500: Internal server error
 */
