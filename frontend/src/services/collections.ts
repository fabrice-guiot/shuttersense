/**
 * Collection API service
 *
 * Handles all API calls related to photo collections
 */

import api from './api'
import type {
  Collection,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionListQueryParams,
  CollectionTestResponse,
  CollectionDeleteResponse
} from '@/contracts/api/collection-api'

/**
 * List all collections with optional filters
 */
export const listCollections = async (filters: CollectionListQueryParams = {}): Promise<Collection[]> => {
  const params: CollectionListQueryParams = {}
  if (filters.state) params.state = filters.state
  if (filters.type) params.type = filters.type
  if (filters.accessible_only) params.accessible_only = true
  if (filters.limit) params.limit = filters.limit
  if (filters.offset) params.offset = filters.offset

  const response = await api.get<Collection[]>('/collections', { params })
  return response.data
}

/**
 * Get a single collection by ID
 */
export const getCollection = async (id: number): Promise<Collection> => {
  const response = await api.get<Collection>(`/collections/${id}`)
  return response.data
}

/**
 * Create a new collection
 */
export const createCollection = async (data: CollectionCreateRequest): Promise<Collection> => {
  const response = await api.post<Collection>('/collections', data)
  return response.data
}

/**
 * Update an existing collection
 */
export const updateCollection = async (id: number, data: CollectionUpdateRequest): Promise<Collection> => {
  const response = await api.put<Collection>(`/collections/${id}`, data)
  return response.data
}

/**
 * Delete a collection
 * @returns Returns result info if collection has data, void if deleted
 * @throws Error 409 if results/jobs exist and force=false
 */
export const deleteCollection = async (
  id: number,
  force = false
): Promise<CollectionDeleteResponse | void> => {
  const params = force ? { force_delete: force } : {}
  const response = await api.delete<CollectionDeleteResponse>(`/collections/${id}`, { params })
  // If status is 200, return the result/job info
  if (response.status === 200) {
    return response.data
  }
  // Status 204 means deleted successfully, no data to return
}

/**
 * Test collection accessibility
 */
export const testCollection = async (id: number): Promise<CollectionTestResponse> => {
  const response = await api.post<CollectionTestResponse>(`/collections/${id}/test`)
  return response.data
}

/**
 * Refresh collection cache
 */
export const refreshCollection = async (id: number, confirm = false): Promise<any> => {
  const params = confirm ? { confirm: true } : {}
  const response = await api.post(`/collections/${id}/refresh`, null, { params })
  return response.data
}
