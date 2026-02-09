/**
 * Category API Contracts
 *
 * Defines TypeScript interfaces for all category-related API endpoints.
 * Issue #39 - Calendar Events feature (Phase 3)
 */

import type { AuditInfo } from './audit-api'

// ============================================================================
// Entity Types
// ============================================================================

export interface Category {
  guid: string              // External identifier (cat_xxx format)
  name: string
  icon: string | null       // Lucide icon name
  color: string | null      // Hex color code (e.g., "#3B82F6")
  is_active: boolean
  display_order: number
  created_at: string        // ISO 8601 timestamp
  updated_at: string        // ISO 8601 timestamp
  audit?: AuditInfo | null
}

// ============================================================================
// API Request Types
// ============================================================================

export interface CategoryCreateRequest {
  name: string
  icon?: string | null
  color?: string | null
  is_active?: boolean
  display_order?: number
}

export interface CategoryUpdateRequest {
  name?: string
  icon?: string | null
  color?: string | null
  is_active?: boolean
}

export interface CategoryReorderRequest {
  ordered_guids: string[]
}

// ============================================================================
// API Response Types
// ============================================================================

export interface CategoryListResponse {
  items: Category[]
  total: number
}

export interface CategorySeedResponse {
  /** Number of new default categories created */
  categories_created: number

  /** Full list of categories after seeding */
  categories: Category[]
}

export interface CategoryStatsResponse {
  /** Total number of categories */
  total_count: number

  /** Number of active categories (is_active=true) */
  active_count: number

  /** Number of inactive categories */
  inactive_count: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface CategoryErrorResponse {
  detail: string
  code?: string
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/categories
 *
 * List all categories
 *
 * Query Parameters:
 *   - is_active: boolean (optional) - Filter by active status
 * Response: 200 Category[]
 * Errors:
 *   - 500: Internal server error
 */

/**
 * POST /api/categories
 *
 * Create a new category
 *
 * Request Body: CategoryCreateRequest
 * Response: 201 Category
 * Errors:
 *   - 400: Validation error (invalid color format)
 *   - 409: Category with this name already exists
 *   - 500: Internal server error
 */

/**
 * GET /api/categories/{guid}
 *
 * Get category by GUID
 *
 * Path Parameters:
 *   - guid: string (category GUID, cat_xxx format)
 * Response: 200 Category
 * Errors:
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * PATCH /api/categories/{guid}
 *
 * Update existing category
 *
 * Path Parameters:
 *   - guid: string (category GUID, cat_xxx format)
 * Request Body: CategoryUpdateRequest
 * Response: 200 Category
 * Errors:
 *   - 400: Validation error
 *   - 404: Category not found
 *   - 409: Category name conflict
 *   - 500: Internal server error
 */

/**
 * DELETE /api/categories/{guid}
 *
 * Delete category
 *
 * Path Parameters:
 *   - guid: string (category GUID, cat_xxx format)
 * Response: 204 No Content
 * Errors:
 *   - 404: Category not found
 *   - 409: Category in use (has events, locations, etc.)
 *   - 500: Internal server error
 */

/**
 * POST /api/categories/reorder
 *
 * Reorder categories
 *
 * Request Body: CategoryReorderRequest
 * Response: 200 Category[]
 * Errors:
 *   - 404: Category GUID not found
 *   - 500: Internal server error
 */

/**
 * GET /api/categories/stats
 *
 * Get category statistics (KPIs)
 *
 * Response: 200 CategoryStatsResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * POST /api/categories/seed-defaults
 *
 * Restore missing default categories (idempotent)
 *
 * Response: 200 CategorySeedResponse
 * Errors:
 *   - 500: Internal server error
 */
