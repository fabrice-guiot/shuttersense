/**
 * Tests for useCameras and useCameraStats hooks
 *
 * Issue #217 - Pipeline-Driven Analysis Tools (US4)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useCameras, useCameraStats } from '../useCameras'
import * as cameraService from '@/services/cameras'
import type { CameraResponse, CameraListResponse, CameraStatsResponse } from '@/contracts/api/camera-api'

// Mock the service
vi.mock('@/services/cameras')

describe('useCameras', () => {
  const mockCameras: CameraResponse[] = [
    {
      guid: 'cam_01hgw2bbg00000000000000001',
      camera_id: 'AB3D',
      status: 'confirmed',
      display_name: 'Canon EOS R5',
      make: 'Canon',
      model: 'EOS R5',
      serial_number: '12345',
      notes: null,
      metadata_json: null,
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: null,
    },
    {
      guid: 'cam_01hgw2bbg00000000000000002',
      camera_id: 'XY5Z',
      status: 'temporary',
      display_name: null,
      make: null,
      model: null,
      serial_number: null,
      notes: null,
      metadata_json: null,
      created_at: '2026-01-16T10:00:00Z',
      updated_at: '2026-01-16T10:00:00Z',
      audit: null,
    },
  ]

  const mockListResponse: CameraListResponse = {
    items: mockCameras,
    total: 2,
    limit: 50,
    offset: 0,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cameraService.listCameras).mockResolvedValue(mockListResponse)
    vi.mocked(cameraService.updateCamera).mockResolvedValue(mockCameras[0])
    vi.mocked(cameraService.deleteCamera).mockResolvedValue({
      message: 'Camera deleted',
      deleted_guid: mockCameras[0].guid,
    })
  })

  it('should fetch cameras on mount', async () => {
    const { result } = renderHook(() => useCameras())

    expect(result.current.loading).toBe(true)
    expect(result.current.cameras).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.cameras).toHaveLength(2)
    expect(result.current.total).toBe(2)
    expect(result.current.cameras[0].camera_id).toBe('AB3D')
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useCameras({ autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.cameras).toEqual([])
    expect(cameraService.listCameras).not.toHaveBeenCalled()
  })

  it('should fetch cameras with filters', async () => {
    const { result } = renderHook(() => useCameras({ autoFetch: false }))

    await act(async () => {
      await result.current.fetchCameras({ status: 'confirmed', search: 'Canon' })
    })

    expect(cameraService.listCameras).toHaveBeenCalledWith({ status: 'confirmed', search: 'Canon' })
    expect(result.current.cameras).toHaveLength(2)
  })

  it('should update a camera', async () => {
    const updatedCamera: CameraResponse = {
      ...mockCameras[0],
      display_name: 'Updated Name',
    }
    vi.mocked(cameraService.updateCamera).mockResolvedValue(updatedCamera)

    const { result } = renderHook(() => useCameras())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let updated: CameraResponse | undefined

    await act(async () => {
      updated = await result.current.updateCamera(mockCameras[0].guid, {
        display_name: 'Updated Name',
      })
    })

    expect(updated?.display_name).toBe('Updated Name')
    expect(cameraService.updateCamera).toHaveBeenCalledWith(
      mockCameras[0].guid,
      { display_name: 'Updated Name' }
    )
  })

  it('should delete a camera', async () => {
    const { result } = renderHook(() => useCameras())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.cameras).toHaveLength(2)

    await act(async () => {
      await result.current.deleteCamera(mockCameras[0].guid)
    })

    expect(cameraService.deleteCamera).toHaveBeenCalledWith(mockCameras[0].guid)
    // Local state should remove the deleted camera
    expect(result.current.cameras).toHaveLength(1)
    expect(result.current.total).toBe(1)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load cameras'
    vi.mocked(cameraService.listCameras).mockRejectedValue(error)

    const { result } = renderHook(() => useCameras({ autoFetch: false }))

    await act(async () => {
      try {
        await result.current.fetchCameras()
      } catch {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to load cameras')
    expect(result.current.cameras).toEqual([])
  })

  it('should handle update error', async () => {
    const error = new Error('Not found')
    ;(error as any).userMessage = 'Camera not found'
    vi.mocked(cameraService.updateCamera).mockRejectedValue(error)

    const { result } = renderHook(() => useCameras())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.updateCamera('cam_invalid', { status: 'confirmed' })
        expect.fail('Should have thrown')
      } catch {
        // Expected
      }
    })

    expect(result.current.error).toBe('Camera not found')
  })

  it('should handle delete error', async () => {
    const error = new Error('Not found')
    ;(error as any).userMessage = 'Camera not found'
    vi.mocked(cameraService.deleteCamera).mockRejectedValue(error)

    const { result } = renderHook(() => useCameras())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.deleteCamera('cam_invalid')
        expect.fail('Should have thrown')
      } catch {
        // Expected
      }
    })

    expect(result.current.error).toBe('Camera not found')
  })

  it('should refetch with last params', async () => {
    const { result } = renderHook(() => useCameras({ autoFetch: false }))

    await act(async () => {
      await result.current.fetchCameras({ status: 'temporary' })
    })

    expect(cameraService.listCameras).toHaveBeenCalledTimes(1)

    await act(async () => {
      await result.current.refetch()
    })

    expect(cameraService.listCameras).toHaveBeenCalledTimes(2)
    expect(cameraService.listCameras).toHaveBeenLastCalledWith({ status: 'temporary' })
  })
})

describe('useCameraStats', () => {
  const mockStats: CameraStatsResponse = {
    total_cameras: 10,
    confirmed_count: 7,
    temporary_count: 3,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(cameraService.getCameraStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useCameraStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useCameraStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(cameraService.getCameraStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useCameraStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(cameraService.getCameraStats).mockResolvedValue({
      ...mockStats,
      confirmed_count: 8,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.confirmed_count).toBe(8)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load statistics'
    vi.mocked(cameraService.getCameraStats).mockRejectedValue(error)

    const { result } = renderHook(() => useCameraStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load statistics')
    expect(result.current.stats).toBe(null)
  })
})
