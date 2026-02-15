/**
 * Tests for useStorageStats hook
 *
 * Issue #92 - Storage Optimization for Analysis Results
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useStorageStats } from '../useStorageStats'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('useStorageStats', () => {
  const mockStats = {
    total_size_bytes: 1073741824,
    deduplicated_size_bytes: 536870912,
    deduplication_ratio: 50.0,
    total_results: 42,
    unique_results: 35,
    oldest_result_at: '2025-12-01T00:00:00Z',
    newest_result_at: '2026-02-14T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(axios.get).mockResolvedValue({ data: mockStats })
  })

  it('should fetch stats on mount when autoFetch is true', async () => {
    const { result } = renderHook(() => useStorageStats())

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
    expect(axios.get).toHaveBeenCalledWith('/api/analytics/storage')
  })

  it('should not fetch on mount when autoFetch is false', () => {
    const { result } = renderHook(() => useStorageStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(axios.get).not.toHaveBeenCalled()
  })

  it('should handle fetch error', async () => {
    vi.mocked(axios.get).mockRejectedValue({
      response: { data: { detail: 'Storage stats unavailable' } },
    })

    const { result } = renderHook(() => useStorageStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Storage stats unavailable')
    expect(result.current.stats).toBe(null)
  })

  it('should handle network error without response', async () => {
    vi.mocked(axios.get).mockRejectedValue({
      message: 'Network Error',
    })

    const { result } = renderHook(() => useStorageStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network Error')
  })

  it('should refetch stats manually', async () => {
    const { result } = renderHook(() => useStorageStats(false))

    expect(result.current.stats).toBe(null)

    await act(async () => {
      await result.current.fetchStats()
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(axios.get).toHaveBeenCalledTimes(1)
  })

  it('should provide refetch as alias for fetchStats', async () => {
    const { result } = renderHook(() => useStorageStats(false))

    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.stats).toEqual(mockStats)
  })

  it('should clear error state', async () => {
    vi.mocked(axios.get).mockRejectedValue({
      message: 'Network Error',
    })

    const { result } = renderHook(() => useStorageStats())

    await waitFor(() => {
      expect(result.current.error).toBe('Network Error')
    })

    act(() => {
      result.current.clearError()
    })

    expect(result.current.error).toBe(null)
  })
})
