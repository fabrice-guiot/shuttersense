/**
 * Performer API Contracts
 *
 * Defines TypeScript interfaces for all performer-related API endpoints.
 * Issue #39 - Calendar Events feature (Phase 11)
 */

// ============================================================================
// Embedded Types
// ============================================================================

export interface CategorySummary {
  guid: string            // Category GUID (cat_xxx format)
  name: string
  icon: string | null     // Lucide icon name
  color: string | null    // Hex color code
}

// ============================================================================
// Entity Types
// ============================================================================

export interface Performer {
  guid: string                    // External identifier (prf_xxx format)
  name: string
  website: string | null
  instagram_handle: string | null
  instagram_url: string | null    // Full Instagram profile URL (computed)
  category: CategorySummary
  additional_info: string | null
  created_at: string              // ISO 8601 timestamp
  updated_at: string              // ISO 8601 timestamp
}

/** Performer status when associated with an event */
export type PerformerStatus = 'announced' | 'confirmed' | 'cancelled'

/** Performer association with an event */
export interface EventPerformer {
  performer: Performer
  status: PerformerStatus
  added_at: string              // ISO 8601 timestamp
}

/** Minimal performer info for embedding in event responses */
export interface PerformerSummary {
  guid: string
  name: string
  instagram_handle: string | null
  status: PerformerStatus
}

// ============================================================================
// API Request Types
// ============================================================================

export interface PerformerCreateRequest {
  name: string
  category_guid: string
  website?: string | null
  instagram_handle?: string | null
  additional_info?: string | null
}

export interface PerformerUpdateRequest {
  name?: string
  category_guid?: string
  website?: string | null
  instagram_handle?: string | null
  additional_info?: string | null
}

/** Request to add a performer to an event */
export interface EventPerformerAddRequest {
  performer_guid: string
  status?: PerformerStatus
}

/** Request to update a performer's status at an event */
export interface EventPerformerUpdateRequest {
  status: PerformerStatus
}

// ============================================================================
// API Response Types
// ============================================================================

export interface PerformerListResponse {
  items: Performer[]
  total: number
}

export interface PerformerStatsResponse {
  /** Total number of performers */
  total_count: number

  /** Number of performers with Instagram handles */
  with_instagram_count: number

  /** Number of performers with websites */
  with_website_count: number
}

export interface CategoryMatchResponse {
  matches: boolean
}

export interface EventPerformersListResponse {
  items: EventPerformer[]
  total: number
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface PerformerListParams {
  category_guid?: string
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface PerformerErrorResponse {
  detail: string
  code?: string
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/performers
 *
 * List all performers with optional filtering
 *
 * Query Parameters:
 *   - category_guid: string (optional) - Filter by category
 *   - search: string (optional) - Search in name, instagram, additional_info
 *   - limit: number (optional, default: 100) - Max results
 *   - offset: number (optional, default: 0) - Pagination offset
 * Response: 200 PerformerListResponse
 * Errors:
 *   - 404: Category not found (if filtering by invalid category)
 *   - 500: Internal server error
 */

/**
 * POST /api/performers
 *
 * Create a new performer
 *
 * Request Body: PerformerCreateRequest
 * Response: 201 Performer
 * Errors:
 *   - 400: Validation error (inactive category)
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/performers/{guid}
 *
 * Get performer by GUID
 *
 * Path Parameters:
 *   - guid: string (performer GUID, prf_xxx format)
 * Response: 200 Performer
 * Errors:
 *   - 404: Performer not found
 *   - 500: Internal server error
 */

/**
 * PATCH /api/performers/{guid}
 *
 * Update existing performer
 *
 * Path Parameters:
 *   - guid: string (performer GUID, prf_xxx format)
 * Request Body: PerformerUpdateRequest
 * Response: 200 Performer
 * Errors:
 *   - 400: Validation error
 *   - 404: Performer or category not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/performers/{guid}
 *
 * Delete performer
 *
 * Path Parameters:
 *   - guid: string (performer GUID, prf_xxx format)
 * Response: 204 No Content
 * Errors:
 *   - 404: Performer not found
 *   - 409: Performer in use (has event associations)
 *   - 500: Internal server error
 */

/**
 * GET /api/performers/stats
 *
 * Get performer statistics (KPIs)
 *
 * Response: 200 PerformerStatsResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * GET /api/performers/by-category/{category_guid}
 *
 * Get performers for a specific category (for event assignment)
 *
 * Path Parameters:
 *   - category_guid: string (category GUID, cat_xxx format)
 * Query Parameters:
 *   - search: string (optional) - Search by name
 * Response: 200 Performer[]
 * Errors:
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/performers/{guid}/validate-category/{event_category_guid}
 *
 * Validate that performer's category matches event's category
 *
 * Path Parameters:
 *   - guid: string (performer GUID, prf_xxx format)
 *   - event_category_guid: string (category GUID, cat_xxx format)
 * Response: 200 CategoryMatchResponse
 * Errors:
 *   - 404: Performer not found
 *   - 500: Internal server error
 */
