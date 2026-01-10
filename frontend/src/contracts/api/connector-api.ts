/**
 * Connector API Contracts
 *
 * Defines TypeScript interfaces for all connector-related API endpoints.
 * These contracts mirror the backend FastAPI endpoints (unchanged).
 */

// ============================================================================
// Entity Types
// ============================================================================

export type ConnectorType = 's3' | 'gcs' | 'smb'

export interface Connector {
  guid: string  // External identifier (con_xxx) for URL-safe references
  name: string
  type: ConnectorType
  is_active: boolean
  metadata?: Record<string, unknown> | null
  last_validated?: string | null
  last_error?: string | null
  created_at: string  // ISO 8601 timestamp
  updated_at: string  // ISO 8601 timestamp
}

export type ConnectorCredentials =
  | S3Credentials
  | GCSCredentials
  | SMBCredentials

export interface S3Credentials {
  aws_access_key_id: string
  aws_secret_access_key: string
  region: string
  bucket?: string
}

export interface GCSCredentials {
  service_account_json: string
  bucket?: string
}

export interface SMBCredentials {
  server: string
  share: string
  username: string
  password: string
  domain?: string
}

// ============================================================================
// API Request Types
// ============================================================================

export interface ConnectorCreateRequest {
  name: string
  type: ConnectorType
  credentials: Record<string, unknown>
  metadata?: Record<string, unknown> | null
}

export interface ConnectorUpdateRequest {
  name?: string
  credentials?: Record<string, unknown>
  metadata?: Record<string, unknown> | null
  is_active?: boolean
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ConnectorListResponse {
  connectors: Connector[]
  total: number
}

export interface ConnectorDetailResponse {
  connector: Connector
}

export interface ConnectorTestResponse {
  success: boolean
  message: string
  details?: {
    connection_time_ms?: number
    endpoint?: string
    [key: string]: unknown
  }
}

export interface ConnectorDeleteResponse {
  success: boolean
  message: string
}

// ============================================================================
// API Error Response
// ============================================================================

export interface ConnectorErrorResponse {
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

// Special error case: Cannot delete connector with active collections
export interface ConnectorDeleteConflictResponse {
  error: {
    message: string
    code: 'CONNECTOR_IN_USE'
    details: {
      collection_count: number
      collection_guids: string[]
    }
  }
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/connectors
 *
 * List all connectors
 *
 * Query Parameters: None
 * Response: 200 ConnectorListResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * POST /api/connectors
 *
 * Create a new connector
 *
 * Request Body: ConnectorCreateRequest
 * Response: 201 ConnectorDetailResponse
 * Errors:
 *   - 400: Invalid request (validation error)
 *   - 409: Connector with this name already exists
 *   - 500: Internal server error
 */

/**
 * GET /api/connectors/{guid}
 *
 * Get connector by GUID
 *
 * Path Parameters:
 *   - guid: string (connector GUID, con_xxx format)
 * Response: 200 ConnectorDetailResponse
 * Errors:
 *   - 404: Connector not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/connectors/{guid}
 *
 * Update existing connector
 *
 * Path Parameters:
 *   - guid: string (connector GUID, con_xxx format)
 * Request Body: ConnectorUpdateRequest
 * Response: 200 ConnectorDetailResponse
 * Errors:
 *   - 400: Invalid request (validation error)
 *   - 404: Connector not found
 *   - 409: Connector name conflict
 *   - 500: Internal server error
 */

/**
 * DELETE /api/connectors/{guid}
 *
 * Delete connector
 *
 * Path Parameters:
 *   - guid: string (connector GUID, con_xxx format)
 * Response: 200 ConnectorDeleteResponse
 * Errors:
 *   - 404: Connector not found
 *   - 409: Connector in use (has collections) - ConnectorDeleteConflictResponse
 *   - 500: Internal server error
 */

/**
 * POST /api/connectors/{guid}/test
 *
 * Test connector connection
 *
 * Path Parameters:
 *   - guid: string (connector GUID, con_xxx format)
 * Request Body: None
 * Response: 200 ConnectorTestResponse
 * Errors:
 *   - 404: Connector not found
 *   - 500: Connection test failed (ConnectorTestResponse with success=false)
 */

// ============================================================================
// KPI Statistics Types (Issue #37)
// ============================================================================

/**
 * Aggregated statistics for all connectors (KPI endpoint)
 *
 * GET /api/connectors/stats
 */
export interface ConnectorStatsResponse {
  /** Total number of connectors */
  total_connectors: number

  /** Number of active connectors (is_active=true) */
  active_connectors: number
}
