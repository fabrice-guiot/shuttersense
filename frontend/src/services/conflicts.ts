/**
 * Conflict Detection & Scoring API service
 *
 * Handles all API calls related to conflict detection, event scoring,
 * conflict resolution, and related configuration.
 * Issue #182 - Calendar Conflict Visualization & Event Picker
 */

import api from './api'
import type {
  ConflictDetectionResponse,
  EventScoreResponse,
  ConflictResolveRequest,
  ConflictResolveResponse,
  ConflictRulesResponse,
  ConflictRulesUpdateRequest,
  ScoringWeightsResponse,
  ScoringWeightsUpdateRequest,
} from '@/contracts/api/conflict-api'

/**
 * Detect conflicts for a date range
 */
export const detectConflicts = async (
  startDate: string,
  endDate: string,
): Promise<ConflictDetectionResponse> => {
  const response = await api.get<ConflictDetectionResponse>('/events/conflicts', {
    params: { start_date: startDate, end_date: endDate },
  })
  return response.data
}

/**
 * Get quality scores for a single event
 */
export const getEventScore = async (guid: string): Promise<EventScoreResponse> => {
  const safeGuid = encodeURIComponent(guid)
  const response = await api.get<EventScoreResponse>(`/events/${safeGuid}/score`)
  return response.data
}

/**
 * Batch-resolve a conflict group
 */
export const resolveConflict = async (
  request: ConflictResolveRequest,
): Promise<ConflictResolveResponse> => {
  const response = await api.post<ConflictResolveResponse>(
    '/events/conflicts/resolve',
    request,
  )
  return response.data
}

/**
 * Get conflict rule settings
 */
export const getConflictRules = async (): Promise<ConflictRulesResponse> => {
  const response = await api.get<ConflictRulesResponse>('/config/conflict_rules')
  return response.data
}

/**
 * Update conflict rule settings (partial update)
 */
export const updateConflictRules = async (
  data: ConflictRulesUpdateRequest,
): Promise<ConflictRulesResponse> => {
  const response = await api.put<ConflictRulesResponse>('/config/conflict_rules', data)
  return response.data
}

/**
 * Get scoring weight settings
 */
export const getScoringWeights = async (): Promise<ScoringWeightsResponse> => {
  const response = await api.get<ScoringWeightsResponse>('/config/scoring_weights')
  return response.data
}

/**
 * Update scoring weight settings (partial update)
 */
export const updateScoringWeights = async (
  data: ScoringWeightsUpdateRequest,
): Promise<ScoringWeightsResponse> => {
  const response = await api.put<ScoringWeightsResponse>('/config/scoring_weights', data)
  return response.data
}
