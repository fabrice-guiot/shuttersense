/**
 * Tools API Contracts
 *
 * Defines TypeScript interfaces for tool execution and job management endpoints.
 * These contracts mirror the backend FastAPI endpoints for Phase 4 implementation.
 */

// ============================================================================
// Entity Types
// ============================================================================

export type ToolType = 'photostats' | 'photo_pairing' | 'pipeline_validation'

export type ToolMode = 'collection' | 'display_graph'

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ProgressData {
  /** Current stage of execution */
  stage: string
  /** Number of files scanned so far (null for display_graph mode) */
  files_scanned: number | null
  /** Total files to scan (null for display_graph mode) */
  total_files: number | null
  /** Number of issues found so far */
  issues_found: number
  /** Percentage complete (0-100) */
  percentage: number
}

export interface Job {
  /** Unique job identifier (UUID) */
  id: string
  /** Collection being analyzed (null for display_graph mode) */
  collection_id: number | null
  /** Tool being executed */
  tool: ToolType
  /** Execution mode for pipeline_validation */
  mode: ToolMode | null
  /** Pipeline ID (for pipeline_validation only) */
  pipeline_id: number | null
  /** Current job status */
  status: JobStatus
  /** Position in queue (null if not queued) */
  position: number | null
  /** When job was created */
  created_at: string // ISO 8601 timestamp
  /** When job started executing */
  started_at: string | null // ISO 8601 timestamp
  /** When job completed */
  completed_at: string | null // ISO 8601 timestamp
  /** Current progress data */
  progress: ProgressData | null
  /** Error message if failed */
  error_message: string | null
  /** Analysis result ID when completed */
  result_id: number | null
}

// ============================================================================
// API Request Types
// ============================================================================

export interface ToolRunRequest {
  /** Tool to execute */
  tool: ToolType
  /** ID of the collection to analyze (required for collection mode) */
  collection_id?: number
  /** Pipeline ID (required for display_graph mode) */
  pipeline_id?: number
  /** Execution mode for pipeline_validation */
  mode?: ToolMode
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface JobListQueryParams {
  /** Filter by job status */
  status?: JobStatus
  /** Filter by collection */
  collection_id?: number
  /** Filter by tool type */
  tool?: ToolType
}

// ============================================================================
// API Response Types
// ============================================================================

export interface JobResponse extends Job {}

export interface JobListResponse {
  jobs: Job[]
}

export interface ConflictResponse {
  /** Conflict message */
  message: string
  /** ID of existing job running on this collection */
  existing_job_id: string
  /** Position of existing job in queue */
  position: number
}

export interface QueueStatusResponse {
  /** Number of queued jobs */
  queued_count: number
  /** Number of running jobs */
  running_count: number
  /** Number of completed jobs (recent) */
  completed_count: number
  /** Number of failed jobs (recent) */
  failed_count: number
  /** Number of cancelled jobs (recent) */
  cancelled_count: number
  /** ID of currently running job (if any) */
  current_job_id: string | null
}

export interface RunAllToolsResponse {
  /** List of created jobs */
  jobs: Job[]
  /** Tools that were skipped (already running) */
  skipped: string[]
  /** Summary message */
  message: string
}

// ============================================================================
// API Error Response
// ============================================================================

export interface ToolsErrorResponse {
  detail: string
  userMessage?: string
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

export interface WebSocketProgressMessage {
  type: 'progress'
  data: ProgressData
}

export interface WebSocketStatusMessage {
  type: 'status'
  status: JobStatus
  result_id?: number
  error_message?: string
}

export interface WebSocketCloseMessage {
  type: 'closed'
  reason: string
}

export type WebSocketMessage =
  | WebSocketProgressMessage
  | WebSocketStatusMessage
  | WebSocketCloseMessage

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * POST /api/tools/run
 *
 * Start tool execution on a collection
 *
 * Request Body: ToolRunRequest
 * Validation Rules:
 *   - pipeline_id required when tool='pipeline_validation'
 *   - Only one job per (collection_id, tool) can be active
 *
 * Response: 202 JobResponse (job accepted and queued)
 * Errors:
 *   - 400: Invalid request (missing fields, invalid tool)
 *   - 409: Tool already running on this collection - ConflictResponse
 *   - 500: Internal server error
 */

/**
 * GET /api/tools/jobs
 *
 * List all jobs with optional filters
 *
 * Query Parameters: JobListQueryParams
 *
 * Response: 200 JobListResponse
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/tools/jobs/{job_id}
 *
 * Get job status and details
 *
 * Path Parameters:
 *   - job_id: string (UUID)
 *
 * Response: 200 JobResponse
 * Errors:
 *   - 404: Job not found
 *   - 500: Internal server error
 */

/**
 * POST /api/tools/jobs/{job_id}/cancel
 *
 * Cancel a queued job
 *
 * Path Parameters:
 *   - job_id: string (UUID)
 *
 * Response: 200 JobResponse (with status=cancelled)
 * Errors:
 *   - 400: Cannot cancel running job
 *   - 404: Job not found
 *   - 500: Internal server error
 */

/**
 * GET /api/tools/queue/status
 *
 * Get queue statistics
 *
 * Response: 200 QueueStatusResponse
 */

/**
 * WebSocket /ws/jobs/{job_id}
 *
 * Connect to receive real-time progress updates for a job
 *
 * Path Parameters:
 *   - job_id: string (UUID)
 *
 * Messages: WebSocketMessage
 *   - type: 'progress' - ProgressData updates
 *   - type: 'status' - Job status changes
 *   - type: 'closed' - Connection closing
 */
