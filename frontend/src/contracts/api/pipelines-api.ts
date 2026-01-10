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
  guid: string  // External identifier (pip_xxx)
  name: string
  description: string | null
  version: number
  is_active: boolean
  is_default: boolean
  is_valid: boolean
  node_count: number
  created_at: string // ISO 8601 timestamp
  updated_at: string // ISO 8601 timestamp
}

export interface Pipeline {
  guid: string  // External identifier (pip_xxx)
  name: string
  description: string | null
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  version: number
  is_active: boolean
  is_default: boolean
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
  // No parameters needed - uses sample_filename from Capture node
}

// ============================================================================
// API Response Types
// ============================================================================

export interface PipelineListResponse {
  items: PipelineSummary[]
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
  /** Number of active pipelines */
  active_pipeline_count: number
  /** GUID of the default pipeline (null if none) */
  default_pipeline_guid: string | null
  /** Name of the default pipeline (null if none) */
  default_pipeline_name: string | null
}

export interface PipelineDeleteResponse {
  message: string
  deleted_guid: string
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface PipelineListQueryParams {
  /** Filter by active status */
  is_active?: boolean
  /** Filter by default status */
  is_default?: boolean
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
    description: 'Defines the base filename structure for camera captures',
    properties: [
      {
        key: 'sample_filename',
        label: 'Sample Filename',
        type: 'string',
        required: true,
        hint: 'A real example base filename (without extension). Example: AB3D0001',
      },
      {
        key: 'filename_regex',
        label: 'Filename Pattern',
        type: 'string',
        required: true,
        hint: 'Regex with exactly 2 capture groups for Camera ID and Counter. Example: ([A-Z0-9]{4})([0-9]{4})',
      },
      {
        key: 'camera_id_group',
        label: 'Camera ID Group',
        type: 'select',
        required: true,
        options: ['1', '2'],
        hint: 'Select which extracted value is the Camera ID (the other will be the Counter, which must be numeric)',
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
    description: 'Defines a processing step with one or more method identifiers',
    properties: [
      {
        key: 'method_ids',
        label: 'Method IDs',
        type: 'array',
        required: false,
        hint: 'Comma-separated processing method identifiers from config.yaml. Example: HDR, BW, Edit (without dashes).',
      },
    ],
  },
  {
    type: 'pairing',
    label: 'Pairing',
    description: 'Groups exactly 2 files together. Inputs are defined by edges pointing to this node.',
    properties: [],
  },
  {
    type: 'branching',
    label: 'Branching',
    description: 'Splits the flow into multiple paths. All paths are explored during validation.',
    properties: [],
  },
  {
    type: 'termination',
    label: 'Termination',
    description: 'End point representing an archival-ready state',
    properties: [
      {
        key: 'termination_type',
        label: 'Termination Type',
        type: 'select',
        required: true,
        options: ['Black Box Archive', 'Browsable Archive'],
        hint: 'Type of archival state this termination node represents',
      },
    ],
  },
]

/**
 * Predefined termination types for pipeline analysis.
 * All pipelines must use these standard termination types.
 */
export const TERMINATION_TYPES = ['Black Box Archive', 'Browsable Archive'] as const
export type TerminationType = typeof TERMINATION_TYPES[number]

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
 * GET /api/pipelines/{guid}
 *
 * Get pipeline details
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * PUT /api/pipelines/{guid}
 *
 * Update pipeline
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 * Request Body: PipelineUpdateRequest
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 400: Validation error
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/pipelines/{guid}
 *
 * Delete pipeline
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 { message, deleted_guid }
 * Errors:
 *   - 404: Pipeline not found
 *   - 409: Cannot delete active pipeline
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/activate
 *
 * Activate pipeline for validation
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 400: Pipeline has validation errors
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/deactivate
 *
 * Deactivate pipeline. If the pipeline is the default, it also loses default status.
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/set-default
 *
 * Set a pipeline as the default for tool execution.
 * Only one pipeline can be default at a time.
 * The pipeline must be active to be set as default.
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 400: Pipeline is not active
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/unset-default
 *
 * Remove default status from a pipeline.
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 Pipeline
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/validate
 *
 * Validate pipeline structure
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 *
 * Response: 200 ValidationResult
 * Errors:
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * POST /api/pipelines/{guid}/preview
 *
 * Preview expected filenames for pipeline
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
 * Request Body: FilenamePreviewRequest
 *
 * Response: 200 FilenamePreviewResponse
 * Errors:
 *   - 400: Pipeline has validation errors
 *   - 404: Pipeline not found
 *   - 500: Internal server error
 */

/**
 * GET /api/pipelines/{guid}/history
 *
 * Get pipeline version history
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
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
 * GET /api/pipelines/{guid}/export
 *
 * Export pipeline as YAML
 *
 * Path Parameters:
 *   - guid: string (pipeline GUID, pip_xxx format)
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
