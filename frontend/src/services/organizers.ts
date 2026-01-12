/**
 * Organizer API service
 *
 * Handles all API calls related to event organizers
 * Issue #39 - Calendar Events feature (Phase 9)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Organizer,
  OrganizerCreateRequest,
  OrganizerUpdateRequest,
  OrganizerListResponse,
  OrganizerListParams,
  OrganizerStatsResponse,
  CategoryMatchResponse
} from '@/contracts/api/organizer-api'

/**
 * List all organizers with optional filters
 */
export const listOrganizers = async (params: OrganizerListParams = {}): Promise<OrganizerListResponse> => {
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

  const response = await api.get<OrganizerListResponse>('/organizers', { params: queryParams })
  return response.data
}

/**
 * Get a single organizer by GUID
 * @param guid - External ID (org_xxx format)
 */
export const getOrganizer = async (guid: string): Promise<Organizer> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'org'))
  const response = await api.get<Organizer>(`/organizers/${safeGuid}`)
  return response.data
}

/**
 * Create a new organizer
 */
export const createOrganizer = async (data: OrganizerCreateRequest): Promise<Organizer> => {
  const response = await api.post<Organizer>('/organizers', data)
  return response.data
}

/**
 * Update an existing organizer
 * @param guid - External ID (org_xxx format)
 */
export const updateOrganizer = async (guid: string, data: OrganizerUpdateRequest): Promise<Organizer> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'org'))
  const response = await api.patch<Organizer>(`/organizers/${safeGuid}`, data)
  return response.data
}

/**
 * Delete an organizer
 * @param guid - External ID (org_xxx format)
 * @throws Error 409 if events reference this organizer
 */
export const deleteOrganizer = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'org'))
  await api.delete(`/organizers/${safeGuid}`)
}

/**
 * Get organizer statistics (KPIs)
 * Returns aggregated stats for all organizers
 */
export const getOrganizerStats = async (): Promise<OrganizerStatsResponse> => {
  const response = await api.get<OrganizerStatsResponse>('/organizers/stats')
  return response.data
}

/**
 * Get organizers filtered by category
 * Used when creating/editing events to show compatible organizers
 *
 * @param categoryGuid - Category GUID (cat_xxx format)
 */
export const getOrganizersByCategory = async (categoryGuid: string): Promise<Organizer[]> => {
  const safeGuid = encodeURIComponent(validateGuid(categoryGuid, 'cat'))
  const response = await api.get<Organizer[]>(`/organizers/by-category/${safeGuid}`)
  return response.data
}

/**
 * Validate that an organizer's category matches an event's category
 *
 * @param organizerGuid - Organizer GUID (org_xxx format)
 * @param eventCategoryGuid - Event's category GUID (cat_xxx format)
 * @returns Whether the categories match
 */
export const validateCategoryMatch = async (
  organizerGuid: string,
  eventCategoryGuid: string
): Promise<boolean> => {
  const safeOrganizerGuid = encodeURIComponent(validateGuid(organizerGuid, 'org'))
  const safeCategoryGuid = encodeURIComponent(validateGuid(eventCategoryGuid, 'cat'))
  const response = await api.get<CategoryMatchResponse>(
    `/organizers/${safeOrganizerGuid}/validate-category/${safeCategoryGuid}`
  )
  return response.data.matches
}
