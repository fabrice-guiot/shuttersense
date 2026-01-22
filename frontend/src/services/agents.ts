/**
 * Agent API service
 *
 * Handles all API calls related to distributed agents
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Agent,
  AgentListResponse,
  AgentUpdateRequest,
  AgentPoolStatusResponse,
  AgentStatsResponse,
  AgentDetailResponse,
  AgentJobHistoryResponse,
  RegistrationToken,
  RegistrationTokenCreateRequest,
  RegistrationTokenListItem,
  RegistrationTokenListResponse,
} from '@/contracts/api/agent-api'

// API base path for agent endpoints (admin endpoints)
const AGENT_API_PATH = '/agent/v1'

// ============================================================================
// Agent CRUD Operations
// ============================================================================

/**
 * List all agents for the current team
 */
export const listAgents = async (includeRevoked = false): Promise<Agent[]> => {
  const params: Record<string, any> = {}
  if (includeRevoked) params.include_revoked = true

  const response = await api.get<AgentListResponse>(`${AGENT_API_PATH}`, { params })
  return response.data.agents
}

/**
 * Get a single agent by GUID
 * @param guid - External ID (agt_xxx format)
 */
export const getAgent = async (guid: string): Promise<Agent> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'agt'))
  const response = await api.get<Agent>(`${AGENT_API_PATH}/${safeGuid}`)
  return response.data
}

/**
 * Update an agent (rename)
 * @param guid - External ID (agt_xxx format)
 */
export const updateAgent = async (guid: string, data: AgentUpdateRequest): Promise<Agent> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'agt'))
  const response = await api.patch<Agent>(`${AGENT_API_PATH}/${safeGuid}`, data)
  return response.data
}

/**
 * Revoke an agent's access
 * @param guid - External ID (agt_xxx format)
 */
export const revokeAgent = async (guid: string, reason?: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'agt'))
  const params: Record<string, any> = {}
  if (reason) params.reason = reason

  await api.delete(`${AGENT_API_PATH}/${safeGuid}`, { params })
}

// ============================================================================
// Agent Pool Status
// ============================================================================

/**
 * Build WebSocket URL for agent endpoints
 * Uses the same base URL as the API client to ensure proper proxying
 */
const buildWebSocketUrl = (path: string): string => {
  const baseUrl = api.defaults.baseURL || '/api'

  // If baseUrl is relative, construct absolute WebSocket URL from current location
  if (baseUrl.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${baseUrl}${path}`
  }

  // If baseUrl is absolute, convert HTTP to WS
  const wsUrl = baseUrl.replace(/^http/, 'ws')
  return `${wsUrl}${path}`
}

/**
 * Get WebSocket URL for agent pool status updates
 * Returns the WebSocket URL for real-time pool status updates
 */
export const getPoolStatusWebSocketUrl = (): string => {
  return buildWebSocketUrl(`${AGENT_API_PATH}/ws/pool-status`)
}

/**
 * Get agent pool status (for header badge)
 */
export const getPoolStatus = async (): Promise<AgentPoolStatusResponse> => {
  const response = await api.get<AgentPoolStatusResponse>(`${AGENT_API_PATH}/pool-status`)
  return response.data
}

/**
 * Get agent statistics (for header KPIs)
 */
export const getAgentStats = async (): Promise<AgentStatsResponse> => {
  // Derive stats from the list response
  const agents = await listAgents()
  return {
    total_agents: agents.length,
    online_agents: agents.filter(a => a.status === 'online').length,
    offline_agents: agents.filter(a => a.status === 'offline').length,
  }
}

// ============================================================================
// Registration Token Operations
// ============================================================================

/**
 * Create a new registration token
 */
export const createRegistrationToken = async (
  data: RegistrationTokenCreateRequest = {}
): Promise<RegistrationToken> => {
  const response = await api.post<RegistrationToken>(`${AGENT_API_PATH}/tokens`, data)
  return response.data
}

/**
 * List registration tokens
 */
export const listRegistrationTokens = async (
  includeUsed = false
): Promise<RegistrationTokenListItem[]> => {
  const params: Record<string, any> = {}
  if (includeUsed) params.include_used = true

  const response = await api.get<RegistrationTokenListResponse>(`${AGENT_API_PATH}/tokens`, {
    params,
  })
  return response.data.tokens
}

/**
 * Delete an unused registration token
 * @param guid - Token GUID (art_xxx format)
 */
export const deleteRegistrationToken = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'art'))
  await api.delete(`${AGENT_API_PATH}/tokens/${safeGuid}`)
}

// ============================================================================
// Agent Detail Operations (Phase 11 - Health Monitoring)
// ============================================================================

/**
 * Get detailed agent information including metrics, stats, and recent jobs
 * @param guid - External ID (agt_xxx format)
 */
export const getAgentDetail = async (guid: string): Promise<AgentDetailResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'agt'))
  const response = await api.get<AgentDetailResponse>(`${AGENT_API_PATH}/${safeGuid}/detail`)
  return response.data
}

/**
 * Get paginated job history for an agent
 * @param guid - External ID (agt_xxx format)
 * @param offset - Number of items to skip (default 0)
 * @param limit - Maximum items to return (default 20)
 */
export const getAgentJobHistory = async (
  guid: string,
  offset = 0,
  limit = 20
): Promise<AgentJobHistoryResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'agt'))
  const response = await api.get<AgentJobHistoryResponse>(`${AGENT_API_PATH}/${safeGuid}/jobs`, {
    params: { offset, limit },
  })
  return response.data
}
