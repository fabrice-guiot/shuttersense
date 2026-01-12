/**
 * Performer API service
 *
 * Handles all API calls related to event performers
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Performer,
  PerformerCreateRequest,
  PerformerUpdateRequest,
  PerformerListResponse,
  PerformerListParams,
  PerformerStatsResponse,
  CategoryMatchResponse
} from '@/contracts/api/performer-api'

/**
 * List all performers with optional filters
 */
export const listPerformers = async (params: PerformerListParams = {}): Promise<PerformerListResponse> => {
  const queryParams: Record<string, string | number | boolean> = {}

  if (params.category_guid !== undefined) {
    queryParams.category_guid = params.category_guid
  }
  if (params.search !== undefined && params.search.trim()) {
    queryParams.search = params.search.trim()
  }
  if (params.limit !== undefined) {
    queryParams.limit = params.limit
  }
  if (params.offset !== undefined) {
    queryParams.offset = params.offset
  }

  const response = await api.get<PerformerListResponse>('/performers', { params: queryParams })
  return response.data
}

/**
 * Get a single performer by GUID
 * @param guid - External ID (prf_xxx format)
 */
export const getPerformer = async (guid: string): Promise<Performer> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'prf'))
  const response = await api.get<Performer>(`/performers/${safeGuid}`)
  return response.data
}

/**
 * Create a new performer
 */
export const createPerformer = async (data: PerformerCreateRequest): Promise<Performer> => {
  const response = await api.post<Performer>('/performers', data)
  return response.data
}

/**
 * Update an existing performer
 * @param guid - External ID (prf_xxx format)
 */
export const updatePerformer = async (guid: string, data: PerformerUpdateRequest): Promise<Performer> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'prf'))
  const response = await api.patch<Performer>(`/performers/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a performer
 * @param guid - External ID (prf_xxx format)
 * @throws Error 409 if events reference this performer
 */
export const deletePerformer = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'prf'))
  await api.delete(`/performers/${safeGuid}`)
}

/**
 * Get performer statistics (KPIs)
 * Returns aggregated stats for all performers
 */
export const getPerformerStats = async (): Promise<PerformerStatsResponse> => {
  const response = await api.get<PerformerStatsResponse>('/performers/stats')
  return response.data
}

/**
 * Get performers filtered by category
 * Used when creating/editing events to show compatible performers
 *
 * @param categoryGuid - Category GUID (cat_xxx format)
 * @param search - Optional search term for performer name
 */
export const getPerformersByCategory = async (
  categoryGuid: string,
  search?: string
): Promise<Performer[]> => {
  const safeGuid = encodeURIComponent(validateGuid(categoryGuid, 'cat'))
  const params: Record<string, string> = {}
  if (search?.trim()) {
    params.search = search.trim()
  }
  const response = await api.get<Performer[]>(`/performers/by-category/${safeGuid}`, { params })
  return response.data
}

/**
 * Validate that a performer's category matches an event's category
 *
 * @param performerGuid - Performer GUID (prf_xxx format)
 * @param eventCategoryGuid - Event's category GUID (cat_xxx format)
 * @returns Whether the categories match
 */
export const validatePerformerCategoryMatch = async (
  performerGuid: string,
  eventCategoryGuid: string
): Promise<boolean> => {
  const safePerformerGuid = encodeURIComponent(validateGuid(performerGuid, 'prf'))
  const safeCategoryGuid = encodeURIComponent(validateGuid(eventCategoryGuid, 'cat'))
  const response = await api.get<CategoryMatchResponse>(
    `/performers/${safePerformerGuid}/validate-category/${safeCategoryGuid}`
  )
  return response.data.matches
}
