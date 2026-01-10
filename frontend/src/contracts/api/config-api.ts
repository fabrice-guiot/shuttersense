/**
 * Configuration API Contracts
 *
 * Defines TypeScript interfaces for configuration management endpoints.
 * These contracts mirror the backend FastAPI endpoints for Phase 7 implementation.
 */

// ============================================================================
// Entity Types
// ============================================================================

export type ConfigCategory = 'extensions' | 'cameras' | 'processing_methods'

export type ConfigSource = 'database' | 'yaml_import'

export type ImportSessionStatus = 'pending' | 'resolved' | 'applied' | 'cancelled' | 'expired'

export type ConflictResolution = 'use_database' | 'use_yaml'

// ============================================================================
// Configuration Structures
// ============================================================================

export interface ExtensionsConfig {
  /** List of photo file extensions */
  photo_extensions: string[]
  /** List of metadata file extensions */
  metadata_extensions: string[]
  /** Extensions that require sidecar files */
  require_sidecar: string[]
}

export interface CameraConfig {
  /** Camera display name */
  name: string
  /** Camera serial number */
  serial_number: string
}

export interface ConfigItem {
  /** Configuration key */
  key: string
  /** Configuration value (type varies by category) */
  value: unknown
  /** Optional description */
  description: string | null
  /** Source of this configuration */
  source: ConfigSource
  /** Last modification timestamp */
  updated_at: string // ISO 8601 timestamp
}

// ============================================================================
// Configuration Response Types
// ============================================================================

export interface ConfigurationResponse {
  extensions: ExtensionsConfig
  cameras: Record<string, CameraConfig>
  processing_methods: Record<string, string>
}

export interface CategoryConfigResponse {
  category: ConfigCategory
  items: ConfigItem[]
}

export interface ConfigValueResponse {
  category: ConfigCategory
  key: string
  value: unknown
  description: string | null
  source: ConfigSource
  updated_at: string // ISO 8601 timestamp
}

export interface ConfigStatsResponse {
  /** Total number of configuration items */
  total_items: number
  /** Number of cameras configured */
  cameras_configured: number
  /** Number of processing methods configured */
  processing_methods_configured: number
  /** Last import timestamp */
  last_import: string | null // ISO 8601 timestamp
  /** Breakdown by source */
  source_breakdown: {
    database: number
    yaml_import: number
  }
}

// ============================================================================
// Import/Export Types
// ============================================================================

export interface ConfigConflict {
  /** Category of the conflicting config */
  category: ConfigCategory
  /** Key of the conflicting config */
  key: string
  /** Current value in database */
  database_value: unknown
  /** Value from YAML file */
  yaml_value: unknown
  /** Whether this conflict has been resolved */
  resolved: boolean
  /** Resolution choice (if resolved) */
  resolution: ConflictResolution | null
}

export interface ImportSessionResponse {
  /** Session identifier (GUID format: imp_xxx) */
  session_id: string
  /** Current session status */
  status: ImportSessionStatus
  /** When session expires */
  expires_at: string // ISO 8601 timestamp
  /** Original file name */
  file_name: string
  /** Total items in YAML file */
  total_items: number
  /** New items (not in database) */
  new_items: number
  /** Conflicts requiring resolution */
  conflicts: ConfigConflict[]
}

export interface ImportResultResponse {
  /** Whether import succeeded */
  success: boolean
  /** Number of items imported */
  items_imported: number
  /** Number of items skipped */
  items_skipped: number
  /** Summary message */
  message: string
}

// ============================================================================
// API Request Types
// ============================================================================

export interface CategoryConfigUpdateRequest {
  items: Array<{
    key: string
    value: unknown
    description?: string
  }>
}

export interface ConfigValueUpdateRequest {
  value: unknown
  description?: string
}

export interface ConflictResolutionRequest {
  resolutions: Array<{
    category: ConfigCategory
    key: string
    use_yaml: boolean
  }>
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface ConfigQueryParams {
  /** Filter by category */
  category?: ConfigCategory
}

// ============================================================================
// API Error Response
// ============================================================================

export interface ConfigErrorResponse {
  detail: string
  userMessage?: string
}

// ============================================================================
// Frontend-Specific Types
// ============================================================================

/**
 * Extended ConfigItem for frontend editing
 */
export interface EditableConfigItem extends ConfigItem {
  isEditing: boolean
  editedValue: unknown
  hasChanges: boolean
}

/**
 * Import wizard step
 */
export type ImportWizardStep = 'upload' | 'review' | 'resolve' | 'confirm' | 'complete'

/**
 * Import wizard state
 */
export interface ImportWizardState {
  step: ImportWizardStep
  session: ImportSessionResponse | null
  pendingResolutions: Map<string, boolean> // key = `${category}:${key}`, value = use_yaml
  isLoading: boolean
  error: string | null
}

/**
 * Get conflict key for map lookups
 */
export function getConflictKey(category: ConfigCategory, key: string): string {
  return `${category}:${key}`
}

/**
 * Parse conflict key
 */
export function parseConflictKey(conflictKey: string): { category: ConfigCategory; key: string } {
  const [category, key] = conflictKey.split(':')
  return { category: category as ConfigCategory, key }
}

/**
 * Category display names
 */
export const CATEGORY_LABELS: Record<ConfigCategory, string> = {
  extensions: 'File Extensions',
  cameras: 'Camera Mappings',
  processing_methods: 'Processing Methods',
}

/**
 * Category descriptions
 */
export const CATEGORY_DESCRIPTIONS: Record<ConfigCategory, string> = {
  extensions: 'Configure photo and metadata file extensions',
  cameras: 'Map camera IDs to camera names and serial numbers',
  processing_methods: 'Define processing method codes and descriptions',
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/config
 *
 * Get all configuration
 *
 * Query Parameters: ConfigQueryParams
 *
 * Response: 200 ConfigurationResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * GET /api/config/{category}
 *
 * Get configuration for a category
 *
 * Path Parameters:
 *   - category: ConfigCategory
 *
 * Response: 200 CategoryConfigResponse
 * Errors:
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/config/{category}
 *
 * Update configuration for a category
 *
 * Path Parameters:
 *   - category: ConfigCategory
 * Request Body: CategoryConfigUpdateRequest
 *
 * Response: 200 CategoryConfigResponse
 * Errors:
 *   - 400: Validation error
 *   - 404: Category not found
 *   - 500: Internal server error
 */

/**
 * GET /api/config/{category}/{key}
 *
 * Get a specific configuration value
 *
 * Path Parameters:
 *   - category: ConfigCategory
 *   - key: string
 *
 * Response: 200 ConfigValueResponse
 * Errors:
 *   - 404: Configuration not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/config/{category}/{key}
 *
 * Update a specific configuration value
 *
 * Path Parameters:
 *   - category: ConfigCategory
 *   - key: string
 * Request Body: ConfigValueUpdateRequest
 *
 * Response: 200 ConfigValueResponse
 * Errors:
 *   - 400: Validation error
 *   - 404: Configuration not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/config/{category}/{key}
 *
 * Delete a configuration value
 *
 * Path Parameters:
 *   - category: ConfigCategory
 *   - key: string
 *
 * Response: 200 { message }
 * Errors:
 *   - 404: Configuration not found
 *   - 500: Internal server error
 */

/**
 * POST /api/config/import
 *
 * Start YAML import with conflict detection
 *
 * Request Body: multipart/form-data with 'file' field
 *
 * Response: 200 ImportSessionResponse
 * Errors:
 *   - 400: Invalid YAML file
 *   - 500: Internal server error
 */

/**
 * GET /api/config/import/{session_id}
 *
 * Get import session status
 *
 * Path Parameters:
 *   - session_id: string (GUID format: imp_xxx)
 *
 * Response: 200 ImportSessionResponse
 * Errors:
 *   - 404: Session not found or expired
 *   - 500: Internal server error
 */

/**
 * POST /api/config/import/{session_id}/resolve
 *
 * Resolve conflicts and apply import
 *
 * Path Parameters:
 *   - session_id: string (GUID format: imp_xxx)
 * Request Body: ConflictResolutionRequest
 *
 * Response: 200 ImportResultResponse
 * Errors:
 *   - 400: Unresolved conflicts remain
 *   - 404: Session not found or expired
 *   - 500: Internal server error
 */

/**
 * POST /api/config/import/{session_id}/cancel
 *
 * Cancel import session
 *
 * Path Parameters:
 *   - session_id: string (GUID format: imp_xxx)
 *
 * Response: 200 { message }
 * Errors:
 *   - 404: Session not found
 *   - 500: Internal server error
 */

/**
 * GET /api/config/export
 *
 * Export configuration as YAML
 *
 * Response: 200 YAML file with Content-Disposition header
 * Errors:
 *   - 500: Internal server error
 */

/**
 * GET /api/config/stats
 *
 * Get configuration statistics for KPIs
 *
 * Response: 200 ConfigStatsResponse
 */
