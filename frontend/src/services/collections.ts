/**
 * Collection API service
 *
 * Handles all API calls related to photo collections
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Collection,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionListQueryParams,
  CollectionTestResponse,
  CollectionDeleteResponse,
  CollectionStatsResponse
} from '@/contracts/api/collection-api'

/**
 * List all collections with optional filters
 */
export const listCollections = async (filters: CollectionListQueryParams = {}): Promise<Collection[]> => {
  const params: CollectionListQueryParams = {}
  if (filters.state) params.state = filters.state
  if (filters.type) params.type = filters.type
  if (filters.accessible_only) params.accessible_only = true
  if (filters.search) params.search = filters.search
  if (filters.limit) params.limit = filters.limit
  if (filters.offset) params.offset = filters.offset

  const response = await api.get<Collection[]>('/collections', { params })
  return response.data
}

/**
 * Get a single collection by GUID
 * @param guid - External ID (col_xxx format)
 */
export const getCollection = async (guid: string): Promise<Collection> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'col'))
  const response = await api.get<Collection>(`/collections/${safeGuid}`)
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
 * @param guid - External ID (col_xxx format)
 */
export const updateCollection = async (guid: string, data: CollectionUpdateRequest): Promise<Collection> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'col'))
  const response = await api.put<Collection>(`/collections/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a collection
 * @param guid - External ID (col_xxx format)
 * @returns Returns result info if collection has data, void if deleted
 * @throws Error 409 if results/jobs exist and force=false
 */
export const deleteCollection = async (
  guid: string,
  force = false
): Promise<CollectionDeleteResponse | void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'col'))
  const params = force ? { force: true } : {}
  const response = await api.delete<CollectionDeleteResponse>(`/collections/${safeGuid}`, { params })
  // If status is 200, return the result/job info
  if (response.status === 200) {
    return response.data
  }
  // Status 204 means deleted successfully, no data to return
}

/**
 * Test collection accessibility
 * @param guid - External ID (col_xxx format)
 */
export const testCollection = async (guid: string): Promise<CollectionTestResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'col'))
  const response = await api.post<CollectionTestResponse>(`/collections/${safeGuid}/test`)
  return response.data
}

/**
 * Refresh collection cache
 * @param guid - External ID (col_xxx format)
 */
export const refreshCollection = async (guid: string, confirm = false): Promise<any> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'col'))
  const params = confirm ? { confirm: true } : {}
  const response = await api.post(`/collections/${safeGuid}/refresh`, null, { params })
  return response.data
}

/**
 * Get collection statistics (KPIs)
 * Returns aggregated stats unaffected by filters
 */
export const getCollectionStats = async (): Promise<CollectionStatsResponse> => {
  const response = await api.get<CollectionStatsResponse>('/collections/stats')
  return response.data
}

/**
 * Assign a pipeline to a collection
 * Stores the pipeline's current version as the pinned version
 * @param collectionGuid - Collection GUID (col_xxx format)
 * @param pipelineGuid - Pipeline GUID (pip_xxx format)
 */
export const assignPipeline = async (collectionGuid: string, pipelineGuid: string): Promise<Collection> => {
  const safeColGuid = encodeURIComponent(validateGuid(collectionGuid, 'col'))
  const safePipGuid = encodeURIComponent(validateGuid(pipelineGuid, 'pip'))
  const response = await api.post<Collection>(
    `/collections/${safeColGuid}/assign-pipeline`,
    null,
    { params: { pipeline_guid: safePipGuid } }
  )
  return response.data
}

/**
 * Clear pipeline assignment from a collection
 * Collection will use default pipeline at runtime
 * @param collectionGuid - Collection GUID (col_xxx format)
 */
export const clearPipeline = async (collectionGuid: string): Promise<Collection> => {
  const safeGuid = encodeURIComponent(validateGuid(collectionGuid, 'col'))
  const response = await api.post<Collection>(`/collections/${safeGuid}/clear-pipeline`)
  return response.data
}
