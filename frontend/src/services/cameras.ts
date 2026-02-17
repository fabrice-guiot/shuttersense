/**
 * Cameras API service
 *
 * Handles all API calls related to camera management
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  CameraResponse,
  CameraListResponse,
  CameraUpdateRequest,
  CameraStatsResponse,
  CameraDeleteResponse,
  CameraListQueryParams,
} from '@/contracts/api/camera-api'

/**
 * List cameras with optional filters and pagination
 */
export const listCameras = async (params: CameraListQueryParams = {}): Promise<CameraListResponse> => {
  const response = await api.get<CameraListResponse>('/cameras', { params })
  return response.data
}

/**
 * Get camera details by GUID
 * @param guid - External ID (cam_xxx format)
 */
export const getCamera = async (guid: string): Promise<CameraResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cam'))
  const response = await api.get<CameraResponse>(`/cameras/${safeGuid}`)
  return response.data
}

/**
 * Update an existing camera
 * @param guid - External ID (cam_xxx format)
 */
export const updateCamera = async (guid: string, data: CameraUpdateRequest): Promise<CameraResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cam'))
  const response = await api.put<CameraResponse>(`/cameras/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a camera
 * @param guid - External ID (cam_xxx format)
 */
export const deleteCamera = async (guid: string): Promise<CameraDeleteResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cam'))
  const response = await api.delete<CameraDeleteResponse>(`/cameras/${safeGuid}`)
  return response.data
}

/**
 * Get camera statistics for KPIs
 */
export const getCameraStats = async (): Promise<CameraStatsResponse> => {
  const response = await api.get<CameraStatsResponse>('/cameras/stats')
  return response.data
}
