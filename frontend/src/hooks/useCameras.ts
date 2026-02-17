/**
 * useCameras React hook
 *
 * Manages camera state with fetch, update, delete operations and stats
 */

import { useState, useEffect, useCallback } from 'react'
import * as camerasService from '../services/cameras'
import type {
  CameraResponse,
  CameraListResponse,
  CameraUpdateRequest,
  CameraListQueryParams,
  CameraStatsResponse,
} from '@/contracts/api/camera-api'

// ============================================================================
// Main Cameras Hook
// ============================================================================

interface UseCamerasOptions {
  autoFetch?: boolean
}

interface UseCamerasReturn {
  cameras: CameraResponse[]
  total: number
  loading: boolean
  error: string | null
  fetchCameras: (params?: CameraListQueryParams) => Promise<void>
  updateCamera: (guid: string, data: CameraUpdateRequest) => Promise<CameraResponse>
  deleteCamera: (guid: string) => Promise<void>
  refetch: () => Promise<void>
}

export const useCameras = (options: UseCamerasOptions = {}): UseCamerasReturn => {
  const { autoFetch = true } = options

  const [cameras, setCameras] = useState<CameraResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastParams, setLastParams] = useState<CameraListQueryParams>({})

  const fetchCameras = useCallback(async (params: CameraListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    setLastParams(params)
    try {
      const data = await camerasService.listCameras(params)
      setCameras(data.items)
      setTotal(data.total)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load cameras'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const updateCamera = useCallback(async (
    guid: string,
    data: CameraUpdateRequest
  ): Promise<CameraResponse> => {
    setLoading(true)
    setError(null)
    try {
      const camera = await camerasService.updateCamera(guid, data)
      return camera
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update camera'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteCamera = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await camerasService.deleteCamera(guid)
      setCameras((prev) => prev.filter((c) => c.guid !== guid))
      setTotal((prev) => prev - 1)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete camera'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const refetch = useCallback(async () => {
    await fetchCameras(lastParams)
  }, [fetchCameras, lastParams])

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchCameras()
    }
  }, [autoFetch, fetchCameras])

  return {
    cameras,
    total,
    loading,
    error,
    fetchCameras,
    updateCamera,
    deleteCamera,
    refetch,
  }
}

// ============================================================================
// Camera Stats Hook (for KPIs)
// ============================================================================

interface UseCameraStatsReturn {
  stats: CameraStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useCameraStats = (autoFetch = true): UseCameraStatsReturn => {
  const [stats, setStats] = useState<CameraStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await camerasService.getCameraStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load camera statistics'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  return { stats, loading, error, refetch }
}
