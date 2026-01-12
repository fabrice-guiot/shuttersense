/**
 * Location API Contracts
 *
 * Defines TypeScript interfaces for all location-related API endpoints.
 * Issue #39 - Calendar Events feature (Phase 8)
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

export interface Location {
  guid: string               // External identifier (loc_xxx format)
  name: string
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  postal_code: string | null
  latitude: number | null
  longitude: number | null
  timezone: string | null    // IANA timezone identifier
  category: CategorySummary
  rating: number | null      // 1-5
  timeoff_required_default: boolean
  travel_required_default: boolean
  notes: string | null
  is_known: boolean          // Whether this is a saved "known location"
  created_at: string         // ISO 8601 timestamp
  updated_at: string         // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface LocationCreateRequest {
  name: string
  category_guid: string
  address?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  postal_code?: string | null
  latitude?: number | null
  longitude?: number | null
  timezone?: string | null
  rating?: number | null
  timeoff_required_default?: boolean
  travel_required_default?: boolean
  notes?: string | null
  is_known?: boolean
}

export interface LocationUpdateRequest {
  name?: string
  category_guid?: string
  address?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  postal_code?: string | null
  latitude?: number | null
  longitude?: number | null
  timezone?: string | null
  rating?: number | null
  timeoff_required_default?: boolean
  travel_required_default?: boolean
  notes?: string | null
  is_known?: boolean
}

export interface GeocodeRequest {
  address: string
}

// ============================================================================
// API Response Types
// ============================================================================

export interface LocationListResponse {
  items: Location[]
  total: number
}

export interface GeocodeResponse {
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  postal_code: string | null
  latitude: number
  longitude: number
  timezone: string | null
}

export interface LocationStatsResponse {
  /** Total number of locations */
  total_count: number

  /** Number of saved "known" locations */
  known_count: number

  /** Number of locations with geocoded coordinates */
  with_coordinates_count: number
}

export interface CategoryMatchResponse {
  matches: boolean
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface LocationListParams {
  category_guid?: string
  known_only?: boolean
  search?: string
  limit?: number
  offset?: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface LocationErrorResponse {
  detail: string
  code?: string
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/locations
 *
 * List all locations with optional filtering
 *
 * Query Parameters:
 *   - category_guid: string (optional) - Filter by category
 *   - known_only: boolean (optional) - Only return saved locations
 *   - search: string (optional) - Search in name, city, address
 *   - limit: number (optional, default: 100) - Max results
 *   - offset: number (optional, default: 0) - Pagination offset
 * Response: 200 LocationListResponse
 * Errors:
 *   - 404: Category not found (if filtering by invalid category)
 *   - 500: Internal server error
 */

/**
 * POST /api/locations
 *
 * Create a new location
 *
 * Request Body: LocationCreateRequest
 * Response: 201 Location
 * Errors:
 *   - 400: Validation error (inactive category, incomplete coordinates)
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/locations/{guid}
 *
 * Get location by GUID
 *
 * Path Parameters:
 *   - guid: string (location GUID, loc_xxx format)
 * Response: 200 Location
 * Errors:
 *   - 404: Location not found
 *   - 500: Internal server error
 */

/**
 * PATCH /api/locations/{guid}
 *
 * Update existing location
 *
 * Path Parameters:
 *   - guid: string (location GUID, loc_xxx format)
 * Request Body: LocationUpdateRequest
 * Response: 200 Location
 * Errors:
 *   - 400: Validation error
 *   - 404: Location or category not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/locations/{guid}
 *
 * Delete location
 *
 * Path Parameters:
 *   - guid: string (location GUID, loc_xxx format)
 * Response: 204 No Content
 * Errors:
 *   - 404: Location not found
 *   - 409: Location in use (has events)
 *   - 500: Internal server error
 */

/**
 * GET /api/locations/stats
 *
 * Get location statistics (KPIs)
 *
 * Response: 200 LocationStatsResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * GET /api/locations/by-category/{category_guid}
 *
 * Get locations for a specific category (for event assignment)
 *
 * Path Parameters:
 *   - category_guid: string (category GUID, cat_xxx format)
 * Query Parameters:
 *   - known_only: boolean (optional, default: true)
 * Response: 200 Location[]
 * Errors:
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * POST /api/locations/geocode
 *
 * Geocode an address to coordinates and timezone
 *
 * Request Body: GeocodeRequest
 * Response: 200 GeocodeResponse
 * Errors:
 *   - 400: Geocoding failed (address not found)
 *   - 500: Internal server error
 */

/**
 * GET /api/locations/{guid}/validate-category/{event_category_guid}
 *
 * Validate that location's category matches event's category
 *
 * Path Parameters:
 *   - guid: string (location GUID, loc_xxx format)
 *   - event_category_guid: string (category GUID, cat_xxx format)
 * Response: 200 CategoryMatchResponse
 * Errors:
 *   - 404: Location not found
 *   - 500: Internal server error
 */
