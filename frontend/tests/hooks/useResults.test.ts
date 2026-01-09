import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useResults, useResult, useResultStats } from '@/hooks/useResults'
import { resetMockData } from '../mocks/handlers'

describe('useResults', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch results on mount', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: true, debounceMs: 0 }))

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.results).toEqual([])

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have 4 mock results
    expect(result.current.results).toHaveLength(4)
    expect(result.current.total).toBe(4)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is disabled', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false }))

    expect(result.current.results).toEqual([])
    expect(result.current.loading).toBe(false)
  })

  it('should fetch results with collection filter', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 50 }))

    // Use setFilters which is the proper API for filtering
    act(() => {
      result.current.setFilters({ collection_id: 1 })
    })

    // Wait for debounced fetch
    await waitFor(() => {
      expect(result.current.results.length).toBeGreaterThan(0)
    }, { timeout: 1000 })

    // All returned results should be from collection 1
    expect(result.current.results.every((r) => r.collection_id === 1)).toBe(true)
  })

  it('should fetch results with tool filter', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 50 }))

    // Use setFilters which is the proper API for filtering
    act(() => {
      result.current.setFilters({ tool: 'photostats' })
    })

    // Wait for debounced fetch
    await waitFor(() => {
      expect(result.current.results.length).toBeGreaterThan(0)
    }, { timeout: 1000 })

    // All returned results should be photostats
    expect(result.current.results.every((r) => r.tool === 'photostats')).toBe(true)
  })

  it('should fetch results with status filter', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 50 }))

    // Use setFilters which is the proper API for filtering
    act(() => {
      result.current.setFilters({ status: 'COMPLETED' })
    })

    // Wait for debounced fetch
    await waitFor(() => {
      expect(result.current.results.length).toBeGreaterThan(0)
    }, { timeout: 1000 })

    // All returned results should be COMPLETED
    expect(result.current.results.every((r) => r.status === 'COMPLETED')).toBe(true)
  })

  it('should handle pagination', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 0, defaultLimit: 2 }))

    // Fetch first page
    await act(async () => {
      await result.current.fetchResults({ limit: 2, offset: 0 })
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.results).toHaveLength(2)
    expect(result.current.total).toBe(4) // Total is still 4

    // Fetch second page
    await act(async () => {
      await result.current.fetchResults({ limit: 2, offset: 2 })
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.results).toHaveLength(2) // 2 results on second page
  })

  it('should delete a result', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: true, debounceMs: 0 }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.results.length
    const resultIdToDelete = result.current.results[0].id

    await act(async () => {
      await result.current.deleteResult(resultIdToDelete)
    })

    expect(result.current.results).toHaveLength(initialCount - 1)
    expect(result.current.total).toBe(initialCount - 1)
    expect(result.current.results.find((r) => r.id === resultIdToDelete)).toBeUndefined()
  })

  it('should fail to delete non-existent result', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false }))

    await act(async () => {
      try {
        await result.current.deleteResult(999)
        expect.fail('Should have thrown 404 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
      }
    })
  })

  it('should update filters and reset page', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 0 }))

    // Set page to 2
    act(() => {
      result.current.setPage(2)
    })

    expect(result.current.page).toBe(2)

    // Set filters - should reset page to 1
    act(() => {
      result.current.setFilters({ tool: 'photostats' })
    })

    expect(result.current.page).toBe(1)
    expect(result.current.filters.tool).toBe('photostats')
  })

  it('should refetch with current filters', async () => {
    const { result } = renderHook(() => useResults({ autoFetch: false, debounceMs: 0 }))

    // Set filter
    act(() => {
      result.current.setFilters({ tool: 'photostats' })
    })

    // Wait for debounce and fetch
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have fetched with tool filter
    expect(result.current.results.every((r) => r.tool === 'photostats')).toBe(true)
  })
})

describe('useResult', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch single result by ID', async () => {
    const { result } = renderHook(() => useResult(1))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.result).toBeDefined()
    expect(result.current.result?.id).toBe(1)
    expect(result.current.result?.tool).toBe('photostats')
    expect(result.current.result?.collection_name).toBe('Test Collection')
    expect(result.current.error).toBe(null)
  })

  it('should handle null resultId', async () => {
    const { result } = renderHook(() => useResult(null))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.result).toBe(null)
  })

  it('should handle non-existent result', async () => {
    const { result } = renderHook(() => useResult(999))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeTruthy()
    expect(result.current.result).toBe(null)
  })

  it('should refetch result', async () => {
    const { result } = renderHook(() => useResult(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.result?.id).toBe(1)
  })

  it('should include full result details including results data', async () => {
    const { result } = renderHook(() => useResult(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.result?.results).toBeDefined()
    // Type narrow to PhotoStatsResults to access its properties
    const photoStatsResults = result.current.result?.results as { total_files: number; total_size: number }
    expect(photoStatsResults?.total_files).toBe(1000)
    expect(photoStatsResults?.total_size).toBe(5000000000)
  })
})

describe('useResultStats', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch result stats on mount', async () => {
    const { result } = renderHook(() => useResultStats(true))

    // Initially loading
    expect(result.current.loading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toBeDefined()
    expect(result.current.stats?.total_results).toBe(4)
    expect(result.current.stats?.completed_count).toBe(3)
    expect(result.current.stats?.failed_count).toBe(1)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useResultStats(false))

    expect(result.current.stats).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should provide stats by tool', async () => {
    const { result } = renderHook(() => useResultStats(true))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats?.by_tool).toBeDefined()
    expect(result.current.stats?.by_tool.photostats).toBe(2)
    expect(result.current.stats?.by_tool.photo_pairing).toBe(1)
    expect(result.current.stats?.by_tool.pipeline_validation).toBe(1)
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useResultStats(false))

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toBeDefined()
  })
})
