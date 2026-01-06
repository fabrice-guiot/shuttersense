/**
 * Pipelines API Contracts
 *
 * Defines TypeScript interfaces for pipeline management endpoints.
 * These contracts mirror the backend FastAPI endpoints for Phase 5 implementation.
 */

// ============================================================================
// Entity Types
// ============================================================================

export type NodeType = 'capture' | 'file' | 'process' | 'pairing' | 'branching' | 'termination'

// Note: Cycles are allowed in pipelines - the CLI pipeline_validation tool
// handles loop execution limits to prevent infinite loops at runtime.
export type ValidationErrorType =
  | 'orphaned_node'
  | 'invalid_reference'
  | 'missing_required_node'
  | 'invalid_property'

export interface PipelineNode {
  /** Unique node identifier within pipeline */
  id: string
  /** Node type determines behavior */
  type: NodeType
  /** Type-specific properties */
  properties: Record<string, unknown>
}

export interface PipelineEdge {
  /** Source node ID */
  from: string
  /** Target node ID */
  to: string
}

export interface ValidationError {
  /** Type of validation error */
  type: ValidationErrorType
  /** Human-readable error message */
  message: string
  /** Node ID where error occurred (if applicable) */
  node_id: string | null
  /** Suggested fix (if available) */
  suggestion: string | null
}

// ============================================================================
// Pipeline Summaries and Full Objects
// ============================================================================

export interface PipelineSummary {
  id: number
  name: string
  description: string | null
  version: number
  is_active: boolean
  is_valid: boolean
  node_count: number
  created_at: string // ISO 8601 timestamp
  updated_at: string // ISO 8601 timestamp
}

export interface Pipeline {
  id: number
  name: string
  description: string | null
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  version: number
  is_active: boolean
  is_valid: boolean
  validation_errors: string[] | null
  created_at: string // ISO 8601 timestamp
  updated_at: string // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface PipelineCreateRequest {
  name: string
  description?: string
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

export interface PipelineUpdateRequest {
  name?: string
  description?: string
  nodes?: PipelineNode[]
  edges?: PipelineEdge[]
  change_summary?: string
}

export interface FilenamePreviewRequest {
  camera_id?: string
  counter?: string
}

// ============================================================================
// API Response Types
// ============================================================================

export interface PipelineListResponse {
  pipelines: PipelineSummary[]
}

export interface PipelineResponse {
  pipeline: Pipeline
}

export interface ValidationResult {
  is_valid: boolean
  errors: ValidationError[]
}

export interface FilenamePreviewResponse {
  base_filename: string
  expected_files: Array<{
    path: string
    filename: string
    optional: boolean
  }>
}

export interface PipelineHistoryEntry {
  id: number
  version: number
  change_summary: string | null
  changed_by: string | null
  created_at: string // ISO 8601 timestamp
}

export interface PipelineStatsResponse {
  /** Total number of pipelines */
  total_pipelines: number
  /** Number of valid pipelines */
  valid_pipelines: number
  /** ID of the active pipeline (null if none) */
  active_pipeline_id: number | null
  /** Name of the active pipeline (null if none) */
  active_pipeline_name: string | null
}

export interface PipelineDeleteResponse {
  message: string
  deleted_id: number
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface PipelineListQueryParams {
  /** Filter by active status */
  is_active?: boolean
  /** Filter by valid status */
  is_valid?: boolean
}

// ============================================================================
// API Error Response
// ============================================================================

export interface PipelinesErrorResponse {
  detail: string
  validation_errors?: ValidationError[]
}

// ============================================================================
// Frontend-Specific Types
// ============================================================================

/**
 * Node type definitions for form editors
 */
export interface NodeTypeDefinition {
  type: NodeType
  label: string
  description: string
  properties: PropertyDefinition[]
}

export interface PropertyDefinition {
  key: string
  label: string
  type: 'string' | 'boolean' | 'number' | 'array' | 'select'
  required: boolean
  options?: string[] // For 'select' type
  default?: unknown
  hint?: string // Helper text with example syntax
}

/**
 * Node type definitions for the form-based editor
 */
export const NODE_TYPE_DEFINITIONS: NodeTypeDefinition[] = [
  {
    type: 'capture',
    label: 'Capture',
    description: 'Defines camera ID and counter patterns',
    properties: [
      {
        key: 'camera_id_pattern',
        label: 'Camera ID Pattern',
        type: 'string',
        required: true,
        hint: 'Regex pattern for camera ID. Example: [A-Z0-9]{4} matches "AB3D"',
      },
      {
        key: 'counter_pattern',
        label: 'Counter Pattern',
        type: 'string',
        required: true,
        hint: 'Regex pattern for counter. Example: [0-9]{4} matches "0001"',
      },
    ],
  },
  {
    type: 'file',
    label: 'File',
    description: 'Defines expected file with extension',
    properties: [
      {
        key: 'extension',
        label: 'Extension',
        type: 'string',
        required: true,
        hint: 'File extension with dot. Example: .dng, .cr3, .xmp',
      },
      {
        key: 'optional',
        label: 'Optional',
        type: 'boolean',
        required: false,
        default: false,
        hint: 'If checked, missing files won\'t cause validation errors',
      },
    ],
  },
  {
    type: 'process',
    label: 'Process',
    description: 'Defines a processing step that may add a suffix',
    properties: [
      {
        key: 'suffix',
        label: 'Suffix',
        type: 'string',
        required: false,
        hint: 'Optional filename suffix indicating processing. Example: -HDR, -BW, -Edit. Leave empty if the process does not transform the filename.',
      },
    ],
  },
  {
    type: 'pairing',
    label: 'Pairing',
    description: 'Groups multiple files together',
    properties: [
      {
        key: 'inputs',
        label: 'Input Node IDs',
        type: 'array',
        required: true,
        hint: 'Comma-separated node IDs to pair. Example: raw_file, xmp_file',
      },
    ],
  },
  {
    type: 'branching',
    label: 'Branching',
    description: 'Conditional branch based on file properties',
    properties: [
      {
        key: 'condition',
        label: 'Condition',
        type: 'select',
        required: true,
        options: ['has_suffix', 'has_extension'],
        hint: 'Property to check for branching decision',
      },
      {
        key: 'value',
        label: 'Value',
        type: 'string',
        required: true,
        hint: 'Value to match. Example: -HDR for suffix, .xmp for extension',
      },
    ],
  },
  {
    type: 'termination',
    label: 'Termination',
    description: 'End point representing an archival-ready state',
    properties: [
      {
        key: 'termination_type',
        label: 'Termination Type',
        type: 'string',
        required: true,
        hint: 'Type of archival state. Example: Black Box Archive, Browsable Archive, Web Export Ready',
      },
    ],
  },
]

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/pipelines
 *
 * List all pipelines with optional filters
 *
 * Query Parameters: PipelineListQueryParams
 *
 * Response: 200 PipelineSummary[]
 * Errors:
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines
 *
 * Create a new pipeline
 *
 * Request Body: PipelineCreateRequest
 *
 * Response: 201 Pipeline
 * Errors:
 *   - 400: Validation error
 *   - 409: Pipeline name already exists
 *   - 500: Internal server error
 */

/**
 * GET /api/pipelines/{pipeline_id}
 *
 * Get pipeline details
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/pipelines/{pipeline_id}
 *
 * Update pipeline
 *
 * Path Parameters:
 *   - pipeline_id: number
 * Request Body: PipelineUpdateRequest
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 400: Validation error
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/pipelines/{pipeline_id}
 *
 * Delete pipeline
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 { message, deleted_id }
 * Errors:
 *   - 404: Pipeline not found
 *   - 409: Cannot delete active pipeline
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{pipeline_id}/activate
 *
 * Activate pipeline for validation
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 400: Pipeline has validation errors
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{pipeline_id}/deactivate
 *
 * Deactivate pipeline
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{pipeline_id}/validate
 *
 * Validate pipeline structure
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 ValidationResult
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{pipeline_id}/preview
 *
 * Preview expected filenames for pipeline
 *
 * Path Parameters:
 *   - pipeline_id: number
 * Request Body: FilenamePreviewRequest
 *
 * Response: 200 FilenamePreviewResponse
 * Errors:
 *   - 400: Pipeline has validation errors
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * GET /api/pipelines/{pipeline_id}/history
 *
 * Get pipeline version history
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 PipelineHistoryEntry[]
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/import
 *
 * Import pipeline from YAML
 *
 * Request Body: multipart/form-data with 'file' field
 *
 * Response: 201 Pipeline
 * Errors:
 *   - 400: Invalid YAML or structure
 *   - 500: Internal server error
 */

/**
 * GET /api/pipelines/{pipeline_id}/export
 *
 * Export pipeline as YAML
 *
 * Path Parameters:
 *   - pipeline_id: number
 *
 * Response: 200 YAML file with Content-Disposition header
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * GET /api/pipelines/stats
 *
 * Get pipeline statistics for KPIs
 *
 * Response: 200 PipelineStatsResponse
 */
