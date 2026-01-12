/**
 * Organizer API Contracts
 *
 * Defines TypeScript interfaces for all organizer-related API endpoints.
 * Issue #39 - Calendar Events feature (Phase 9)
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

export interface Organizer {
  guid: string               // External identifier (org_xxx format)
  name: string
  website: string | null
  category: CategorySummary
  rating: number | null      // 1-5 stars
  ticket_required_default: boolean
  notes: string | null
  created_at: string         // ISO 8601 timestamp
  updated_at: string         // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface OrganizerCreateRequest {
  name: string
  category_guid: string
  website?: string | null
  rating?: number | null
  ticket_required_default?: boolean
  notes?: string | null
}

export interface OrganizerUpdateRequest {
  name?: string
  category_guid?: string
  website?: string | null
  rating?: number | null
  ticket_required_default?: boolean
  notes?: string | null
}

// ============================================================================
// API Response Types
// ============================================================================

export interface OrganizerListResponse {
  items: Organizer[]
  total: number
}

export interface OrganizerStatsResponse {
  /** Total number of organizers */
  total_count: number

  /** Number of organizers with ratings */
  with_rating_count: number

  /** Average rating across rated organizers */
  avg_rating: number | null
}

export interface CategoryMatchResponse {
  matches: boolean
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface OrganizerListParams {
  category_guid?: string
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface OrganizerErrorResponse {
  detail: string
  code?: string
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/organizers
 *
 * List all organizers with optional filtering
 *
 * Query Parameters:
 *   - category_guid: string (optional) - Filter by category
 *   - search: string (optional) - Search in name, website, notes
 *   - limit: number (optional, default: 100) - Max results
 *   - offset: number (optional, default: 0) - Pagination offset
 * Response: 200 OrganizerListResponse
 * Errors:
 *   - 404: Category not found (if filtering by invalid category)
 *   - 500: Internal server error
 */

/**
 * POST /api/organizers
 *
 * Create a new organizer
 *
 * Request Body: OrganizerCreateRequest
 * Response: 201 Organizer
 * Errors:
 *   - 400: Validation error (inactive category, invalid rating)
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/organizers/{guid}
 *
 * Get organizer by GUID
 *
 * Path Parameters:
 *   - guid: string (organizer GUID, org_xxx format)
 * Response: 200 Organizer
 * Errors:
 *   - 404: Organizer not found
 *   - 500: Internal server error
 */

/**
 * PATCH /api/organizers/{guid}
 *
 * Update existing organizer
 *
 * Path Parameters:
 *   - guid: string (organizer GUID, org_xxx format)
 * Request Body: OrganizerUpdateRequest
 * Response: 200 Organizer
 * Errors:
 *   - 400: Validation error
 *   - 404: Organizer or category not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/organizers/{guid}
 *
 * Delete organizer
 *
 * Path Parameters:
 *   - guid: string (organizer GUID, org_xxx format)
 * Response: 204 No Content
 * Errors:
 *   - 404: Organizer not found
 *   - 409: Organizer in use (has events)
 *   - 500: Internal server error
 */

/**
 * GET /api/organizers/stats
 *
 * Get organizer statistics (KPIs)
 *
 * Response: 200 OrganizerStatsResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * GET /api/organizers/by-category/{category_guid}
 *
 * Get organizers for a specific category (for event assignment)
 *
 * Path Parameters:
 *   - category_guid: string (category GUID, cat_xxx format)
 * Response: 200 Organizer[]
 * Errors:
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/organizers/{guid}/validate-category/{event_category_guid}
 *
 * Validate that organizer's category matches event's category
 *
 * Path Parameters:
 *   - guid: string (organizer GUID, org_xxx format)
 *   - event_category_guid: string (category GUID, cat_xxx format)
 * Response: 200 CategoryMatchResponse
 * Errors:
 *   - 404: Organizer not found
 *   - 500: Internal server error
 */
