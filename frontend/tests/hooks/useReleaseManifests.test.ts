/**
 * Tests for useReleaseManifests hook
 *
 * Part of Issue #90 - Distributed Agent Architecture (Phase 14)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useReleaseManifests, useReleaseManifestStats } from '@/hooks/useReleaseManifests'
import * as releaseManifestsApi from '@/services/release-manifests-api'
import type {
  ReleaseManifest,
  ReleaseManifestStatsResponse,
  ReleaseManifestListResponse,
} from '@/contracts/api/release-manifests-api'

// Mock the service
vi.mock('@/services/release-manifests-api')

describe('useReleaseManifests', () => {
  const mockManifests: ReleaseManifest[] = [
    {
      guid: 'rel_01hgw2bbg00000000000000001',
      version: '1.0.0',
      platforms: ['darwin-arm64', 'darwin-amd64'],
      checksum: 'a'.repeat(64),
      is_active: true,
      notes: 'Initial release',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
    },
    {
      guid: 'rel_01hgw2bbg00000000000000002',
      version: '1.1.0',
      platforms: ['linux-amd64'],
      checksum: 'b'.repeat(64),
      is_active: false,
      notes: null,
      created_at: '2026-01-16T10:00:00Z',
      updated_at: '2026-01-16T10:00:00Z',
    },
  ]

  const mockListResponse: ReleaseManifestListResponse = {
    manifests: mockManifests,
    total_count: 2,
    active_count: 1,
  }

  const mockStats: ReleaseManifestStatsResponse = {
    total_count: 2,
    active_count: 1,
    platforms: ['darwin-arm64', 'darwin-amd64', 'linux-amd64'],
    versions: ['1.0.0', '1.1.0'],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(releaseManifestsApi.listManifests).mockResolvedValue(mockListResponse)
    vi.mocked(releaseManifestsApi.getManifestStats).mockResolvedValue(mockStats)
    vi.mocked(releaseManifestsApi.createManifest).mockImplementation(async data => ({
      guid: 'rel_01hgw2bbg00000000000000003',
      ...data,
      notes: data.notes ?? null,
      is_active: data.is_active ?? true,
      created_at: '2026-01-17T10:00:00Z',
      updated_at: '2026-01-17T10:00:00Z',
    }))
    vi.mocked(releaseManifestsApi.updateManifest).mockImplementation(async (guid, data) => {
      const existing = mockManifests.find(m => m.guid === guid)!
      return { ...existing, ...data }
    })
    vi.mocked(releaseManifestsApi.deleteManifest).mockResolvedValue(undefined)
  })

  it('should fetch manifests on mount', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    expect(result.current.loading).toBe(true)
    expect(result.current.manifests).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.manifests).toHaveLength(2)
    expect(result.current.manifests[0].version).toBe('1.0.0')
    expect(result.current.totalCount).toBe(2)
    expect(result.current.activeCount).toBe(1)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useReleaseManifests({ autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.manifests).toEqual([])
    expect(releaseManifestsApi.listManifests).not.toHaveBeenCalled()
  })

  it('should pass filter options to API', async () => {
    renderHook(() => useReleaseManifests({
      activeOnly: true,
      platform: 'darwin-arm64',
      version: '1.0.0'
    }))

    await waitFor(() => {
      expect(releaseManifestsApi.listManifests).toHaveBeenCalledWith({
        active_only: true,
        latest_only: true,
        platform: 'darwin-arm64',
        version: '1.0.0',
      })
    })
  })

  it('should create a manifest and refresh list', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let createdManifest: ReleaseManifest | undefined

    await act(async () => {
      createdManifest = await result.current.createManifest({
        version: '2.0.0',
        platforms: ['linux-arm64'],
        checksum: 'c'.repeat(64),
        notes: 'New version',
      })
    })

    expect(createdManifest?.version).toBe('2.0.0')
    expect(createdManifest?.platforms).toEqual(['linux-arm64'])
    expect(releaseManifestsApi.createManifest).toHaveBeenCalledWith({
      version: '2.0.0',
      platforms: ['linux-arm64'],
      checksum: 'c'.repeat(64),
      notes: 'New version',
    })
    // Should refresh list after create
    expect(releaseManifestsApi.listManifests).toHaveBeenCalledTimes(2)
  })

  it('should update a manifest and refresh list', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let updatedManifest: ReleaseManifest | undefined

    await act(async () => {
      updatedManifest = await result.current.updateManifest(
        'rel_01hgw2bbg00000000000000001',
        { is_active: false, notes: 'Deprecated' }
      )
    })

    expect(updatedManifest?.is_active).toBe(false)
    expect(updatedManifest?.notes).toBe('Deprecated')
    expect(releaseManifestsApi.updateManifest).toHaveBeenCalledWith(
      'rel_01hgw2bbg00000000000000001',
      { is_active: false, notes: 'Deprecated' }
    )
    // Should refresh list after update
    expect(releaseManifestsApi.listManifests).toHaveBeenCalledTimes(2)
  })

  it('should delete a manifest and refresh list', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deleteManifest('rel_01hgw2bbg00000000000000001')
    })

    expect(releaseManifestsApi.deleteManifest).toHaveBeenCalledWith(
      'rel_01hgw2bbg00000000000000001'
    )
    // Should refresh list after delete
    expect(releaseManifestsApi.listManifests).toHaveBeenCalledTimes(2)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    vi.mocked(releaseManifestsApi.listManifests).mockRejectedValue(error)

    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.manifests).toEqual([])
  })

  it('should handle create error', async () => {
    vi.mocked(releaseManifestsApi.createManifest).mockRejectedValue(
      new Error('Duplicate checksum')
    )

    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createManifest({
          version: '1.0.0',
          platforms: ['darwin-arm64'],
          checksum: 'a'.repeat(64),
        })
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Duplicate checksum')
  })

  it('should fetch stats with fetchStats', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
  })

  it('should manually refresh manifests', async () => {
    const { result } = renderHook(() => useReleaseManifests())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.refresh()
    })

    // Initial fetch + manual refresh
    expect(releaseManifestsApi.listManifests).toHaveBeenCalledTimes(2)
  })
})

describe('useReleaseManifestStats', () => {
  const mockStats: ReleaseManifestStatsResponse = {
    total_count: 5,
    active_count: 3,
    platforms: ['darwin-arm64', 'darwin-amd64', 'linux-amd64'],
    versions: ['1.0.0', '1.1.0', '2.0.0'],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(releaseManifestsApi.getManifestStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useReleaseManifestStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.stats?.total_count).toBe(5)
    expect(result.current.stats?.active_count).toBe(3)
    expect(result.current.error).toBe(null)
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useReleaseManifestStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updatedStats: ReleaseManifestStatsResponse = {
      ...mockStats,
      total_count: 6,
      active_count: 4,
    }
    vi.mocked(releaseManifestsApi.getManifestStats).mockResolvedValue(updatedStats)

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.total_count).toBe(6)
    })

    expect(result.current.stats?.active_count).toBe(4)
  })

  it('should handle stats fetch error', async () => {
    vi.mocked(releaseManifestsApi.getManifestStats).mockRejectedValue(
      new Error('Failed to fetch stats')
    )

    const { result } = renderHook(() => useReleaseManifestStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch stats')
    expect(result.current.stats).toBe(null)
  })
})
