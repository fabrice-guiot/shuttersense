/**
 * Agent API Contracts
 *
 * TypeScript types for agent-related API requests and responses.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 */

import type { AuditInfo } from './audit-api'

// ============================================================================
// Agent Status Enum
// ============================================================================

export type AgentStatus = 'online' | 'offline' | 'error' | 'revoked'

// ============================================================================
// Agent Types
// ============================================================================

export interface Agent {
  guid: string
  name: string
  hostname: string
  os_info: string
  status: AgentStatus
  error_message: string | null
  last_heartbeat: string | null
  capabilities: string[]
  authorized_roots: string[]
  version: string
  is_outdated: boolean
  is_verified: boolean
  platform: string | null
  created_at: string
  team_guid: string
  current_job_guid: string | null
  running_jobs_count: number
  audit?: AuditInfo | null
}

export interface AgentListResponse {
  agents: Agent[]
  total_count: number
}

export interface AgentUpdateRequest {
  name: string
}

// ============================================================================
// Agent Pool Status (Header Badge)
// ============================================================================

export interface AgentPoolStatusResponse {
  online_count: number
  offline_count: number
  idle_count: number
  running_jobs_count: number
  outdated_count: number
  unverified_count: number
  status: 'offline' | 'idle' | 'running' | 'outdated'
}

// ============================================================================
// Registration Token Types
// ============================================================================

export interface RegistrationTokenCreateRequest {
  name?: string
  expires_in_hours?: number
}

export interface RegistrationToken {
  guid: string
  token: string
  name: string | null
  expires_at: string
  is_valid: boolean
  created_at: string
  created_by_email: string | null
}

export interface RegistrationTokenListItem {
  guid: string
  name: string | null
  expires_at: string
  is_valid: boolean
  is_used: boolean
  used_by_agent_guid: string | null
  created_at: string
  created_by_email: string | null
  audit?: AuditInfo | null
}

export interface RegistrationTokenListResponse {
  tokens: RegistrationTokenListItem[]
  total_count: number
}

// ============================================================================
// Stats Response (for header KPIs)
// ============================================================================

export interface AgentStatsResponse {
  total_agents: number
  online_agents: number
  offline_agents: number
}

// ============================================================================
// Agent Metrics (Phase 11 - Health Monitoring)
// ============================================================================

export interface AgentMetrics {
  cpu_percent: number | null
  memory_percent: number | null
  disk_free_gb: number | null
}

// ============================================================================
// Agent Job History (Phase 11 - Health Monitoring)
// ============================================================================

export interface AgentJobHistoryItem {
  guid: string
  tool: string
  collection_guid: string | null
  collection_name: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface AgentJobHistoryResponse {
  jobs: AgentJobHistoryItem[]
  total_count: number
  offset: number
  limit: number
}

// ============================================================================
// Active Release Types (Issue #136 - Agent Setup Wizard)
// ============================================================================

export interface ReleaseArtifact {
  /** Platform identifier (e.g., "darwin-arm64") */
  platform: string
  /** Binary filename (e.g., "shuttersense-agent-darwin-arm64") */
  filename: string
  /** sha256:-prefixed hex checksum */
  checksum: string
  /** File size in bytes, or null if unknown */
  file_size: number | null
  /** Relative URL for session-authenticated download. Null if dist dir not configured. */
  download_url: string | null
  /** Time-limited signed URL (default 1 hour expiry). Null if dist dir not configured. */
  signed_url: string | null
}

export interface ActiveReleaseResponse {
  /** Release manifest GUID (rel_xxx format) */
  guid: string
  /** Semantic version */
  version: string
  /** Per-platform artifact entries */
  artifacts: ReleaseArtifact[]
  /** Optional release notes */
  notes: string | null
  /** True if the server is in dev/QA mode (no dist dir configured) */
  dev_mode: boolean
}

// ============================================================================
// Matched Manifest Info (Issue #236 - Agent Attestation)
// ============================================================================

export interface MatchedManifestInfo {
  /** Release manifest GUID (rel_xxx) */
  guid: string
  /** Release version (e.g., "1.0.0") */
  version: string
  /** Supported platforms */
  platforms: string[]
  /** Whether this manifest is currently active */
  is_active: boolean
}

// ============================================================================
// Agent Detail Response (Phase 11 - Health Monitoring)
// ============================================================================

export interface AgentDetailResponse {
  guid: string
  name: string
  hostname: string
  os_info: string
  status: AgentStatus
  error_message: string | null
  last_heartbeat: string | null
  capabilities: string[]
  authorized_roots: string[]
  version: string
  is_outdated: boolean
  is_verified: boolean
  matched_manifest: MatchedManifestInfo | null
  platform: string | null
  created_at: string
  team_guid: string
  current_job_guid: string | null
  metrics: AgentMetrics | null
  bound_collections_count: number
  total_jobs_completed: number
  total_jobs_failed: number
  recent_jobs: AgentJobHistoryItem[]
  audit?: AuditInfo | null
}
