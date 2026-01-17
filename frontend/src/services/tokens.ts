/**
 * API Tokens Service
 *
 * Handles all API calls related to API token management.
 * Phase 10: User Story 7 - API Token Authentication
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  ApiToken,
  ApiTokenCreated,
  CreateTokenRequest,
  TokenStatsResponse,
} from '@/contracts/api/tokens-api'

/**
 * List all tokens created by the current user
 *
 * @param filters - Optional filters
 * @returns List of API tokens (without actual token values)
 */
export const listTokens = async (filters: { active_only?: boolean } = {}): Promise<ApiToken[]> => {
  const params: Record<string, string | boolean> = {}
  if (filters.active_only !== undefined) params.active_only = filters.active_only

  const response = await api.get<ApiToken[]>('/tokens', { params })
  return response.data
}

/**
 * Get a single token by GUID
 *
 * @param guid - Token GUID (tok_xxx format)
 * @returns API token details (without actual token value)
 */
export const getToken = async (guid: string): Promise<ApiToken> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'tok'))
  const response = await api.get<ApiToken>(`/tokens/${safeGuid}`)
  return response.data
}

/**
 * Create a new API token
 *
 * IMPORTANT: The actual token value is only returned once at creation.
 * Store it securely - it cannot be retrieved later!
 *
 * @param data - Token creation data
 * @returns Created token including the actual JWT (only time it's returned!)
 */
export const createToken = async (data: CreateTokenRequest): Promise<ApiTokenCreated> => {
  const response = await api.post<ApiTokenCreated>('/tokens', data)
  return response.data
}

/**
 * Revoke (delete) an API token
 *
 * This deactivates the token - it can no longer be used for authentication.
 *
 * @param guid - Token GUID (tok_xxx format)
 */
export const revokeToken = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'tok'))
  await api.delete(`/tokens/${safeGuid}`)
}

/**
 * Get token statistics
 *
 * @returns Token stats (total, active, revoked counts)
 */
export const getTokenStats = async (): Promise<TokenStatsResponse> => {
  const response = await api.get<TokenStatsResponse>('/tokens/stats')
  return response.data
}
