/**
 * API Token Contract Types
 *
 * Defines TypeScript interfaces for API token management endpoints.
 * Phase 10: User Story 7 - API Token Authentication
 */

// ============================================================================
// Entity Types
// ============================================================================

/**
 * API Token (without the actual token value)
 * Used in list and detail views
 */
export interface ApiToken {
  guid: string              // External identifier (tok_xxx format)
  name: string              // User-provided name/description
  token_prefix: string      // First 8 chars for identification
  scopes: string[]          // Permission scopes (future use)
  expires_at: string        // ISO 8601 timestamp
  last_used_at: string | null // ISO 8601 timestamp or null
  is_active: boolean        // Whether token is active
  created_at: string        // ISO 8601 timestamp
  created_by_guid: string | null // GUID of user who created it
  created_by_email: string | null // Email of user who created it (audit trail)
}

/**
 * Newly created API token (includes the actual token value)
 * Only returned once at creation time - cannot be retrieved again
 */
export interface ApiTokenCreated extends ApiToken {
  token: string             // The actual JWT token - STORE SECURELY!
}

// ============================================================================
// API Request Types
// ============================================================================

/**
 * Request body for creating a new API token
 */
export interface CreateTokenRequest {
  name: string              // Token name/description (1-100 chars)
  expires_in_days?: number  // Days until expiration (1-365, default 90)
}

// ============================================================================
// API Response Types
// ============================================================================

/**
 * List of tokens response (array of ApiToken)
 */
export type TokenListResponse = ApiToken[]

/**
 * Token statistics response
 */
export interface TokenStatsResponse {
  total_count: number
  active_count: number
  revoked_count: number
}

// ============================================================================
// API Endpoint Definitions
// ============================================================================

/**
 * POST /api/tokens
 *
 * Create a new API token
 *
 * Request Body: CreateTokenRequest
 * Response: 201 ApiTokenCreated
 * Errors:
 *   - 400: Validation error
 *   - 403: API tokens cannot create new tokens (require session auth)
 *   - 500: Internal server error
 *
 * NOTE: The actual token value is only returned once at creation.
 * Store it securely - it cannot be retrieved later.
 */

/**
 * GET /api/tokens
 *
 * List tokens created by the current user
 *
 * Query Parameters:
 *   - active_only: boolean (optional) - Filter to only active tokens
 * Response: 200 ApiToken[]
 * Errors:
 *   - 403: API tokens cannot list tokens
 *   - 500: Internal server error
 */

/**
 * GET /api/tokens/{guid}
 *
 * Get token details by GUID
 *
 * Path Parameters:
 *   - guid: string (token GUID, tok_xxx format)
 * Response: 200 ApiToken
 * Errors:
 *   - 403: API tokens cannot view token details
 *   - 404: Token not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/tokens/{guid}
 *
 * Revoke (delete) a token
 *
 * Path Parameters:
 *   - guid: string (token GUID, tok_xxx format)
 * Response: 204 No Content
 * Errors:
 *   - 403: API tokens cannot revoke tokens
 *   - 404: Token not found
 *   - 500: Internal server error
 */
