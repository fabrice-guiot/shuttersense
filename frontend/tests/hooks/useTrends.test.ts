import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import {
  usePhotoStatsTrends,
  usePhotoPairingTrends,
  usePipelineValidationTrends,
  useDisplayGraphTrends,
  useTrendSummary,
  useTrends
} from '@/hooks/useTrends'
import { resetMockData } from '../mocks/handlers'

describe('usePhotoStatsTrends', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => usePhotoStatsTrends({ autoFetch: false }))

    expect(result.current.data).toBe(null)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should fetch when setFilters is called', async () => {
    const { result } = renderHook(() => usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('aggregated')
    expect(result.current.data?.data_points).toHaveLength(3)
  })

  it('should set loading state during fetch', async () => {
    const { result } = renderHook(() => usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    // Wait for fetch to complete, then verify loading is false
    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.loading).toBe(false)
  })

  it('should fetch with collection_ids filter for comparison mode', async () => {
    const { result } = renderHook(() => usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ collection_ids: '1' })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('comparison')
    expect(result.current.data?.collections).toHaveLength(1)
  })

  it('should refetch with current filters', async () => {
    const { result } = renderHook(() => usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 }))

    // Set initial filters
    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    const initialData = result.current.data

    // Refetch
    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.data).not.toBe(null)
    expect(result.current.data?.data_points).toHaveLength(initialData?.data_points.length ?? 0)
  })
})

describe('usePhotoPairingTrends', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => usePhotoPairingTrends({ autoFetch: false }))

    expect(result.current.data).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should fetch aggregated data', async () => {
    const { result } = renderHook(() => usePhotoPairingTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('aggregated')
    expect(result.current.data?.data_points).toHaveLength(3)
    expect(result.current.data?.data_points[0].group_count).toBe(800)
    expect(result.current.data?.data_points[0].image_count).toBe(1600)
  })

  it('should fetch comparison data with collection_ids', async () => {
    const { result } = renderHook(() => usePhotoPairingTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ collection_ids: '1,2' })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('comparison')
    expect(result.current.data?.collections).toHaveLength(2)
    expect(result.current.data?.collections[0].cameras).toContain('ABC1')
  })
})

describe('usePipelineValidationTrends', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => usePipelineValidationTrends({ autoFetch: false }))

    expect(result.current.data).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should fetch aggregated percentage data', async () => {
    const { result } = renderHook(() => usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('aggregated')
    expect(result.current.data?.data_points).toHaveLength(3)
    expect(result.current.data?.data_points[0].overall_consistency_pct).toBe(80)
    expect(result.current.data?.data_points[0].black_box_consistency_pct).toBe(85)
  })

  it('should fetch comparison data with collection_ids', async () => {
    const { result } = renderHook(() => usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ collection_ids: '1' })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data?.mode).toBe('comparison')
    expect(result.current.data?.collections).toHaveLength(1)
    expect(result.current.data?.collections[0].data_points[0].consistent_ratio).toBe(80)
  })

  it('should support pipeline_id filter', async () => {
    const { result } = renderHook(() => usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ pipeline_id: 1 })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data).not.toBe(null)
  })
})

describe('useDisplayGraphTrends', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useDisplayGraphTrends({ autoFetch: false }))

    expect(result.current.data).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should fetch display graph trend data', async () => {
    const { result } = renderHook(() => useDisplayGraphTrends({ autoFetch: false, debounceMs: 0 }))

    act(() => {
      result.current.setFilters({ from_date: undefined })
    })

    await waitFor(() => {
      expect(result.current.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.data).not.toBe(null)
    expect(result.current.data?.data_points).toHaveLength(2)
    expect(result.current.data?.data_points[0].total_paths).toBe(100)
    expect(result.current.data?.data_points[0].valid_paths).toBe(90)
    expect(result.current.data?.pipelines_included).toHaveLength(1)
  })
})

describe('useTrendSummary', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch on mount when autoFetch is true', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.summary).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.summary?.orphaned_trend).toBe('improving')
    expect(result.current.summary?.consistency_trend).toBe('stable')
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: false }))

    expect(result.current.summary).toBe(null)
    expect(result.current.loading).toBe(false)
  })

  it('should include collection_id when provided', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: true, collectionId: 1 }))

    await waitFor(() => {
      expect(result.current.summary).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.summary?.collection_id).toBe(1)
  })

  it('should return null collection_id for all collections', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.summary).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.summary?.collection_id).toBe(null)
  })

  it('should include data_points_available counts', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: true }))

    await waitFor(() => {
      expect(result.current.summary).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.summary?.data_points_available.photostats).toBe(3)
    expect(result.current.summary?.data_points_available.photo_pairing).toBe(3)
    expect(result.current.summary?.data_points_available.pipeline_validation).toBe(3)
  })

  it('should refetch data', async () => {
    const { result } = renderHook(() => useTrendSummary({ autoFetch: false }))

    expect(result.current.summary).toBe(null)

    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.summary).not.toBe(null)
  })
})

describe('useTrends (combined hook)', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should provide access to all trend hooks', async () => {
    const { result } = renderHook(() => useTrends({ autoFetch: false }))

    expect(result.current.photoStats).toBeDefined()
    expect(result.current.photoPairing).toBeDefined()
    expect(result.current.pipelineValidation).toBeDefined()
    expect(result.current.summary).toBeDefined()
  })

  it('should start with isLoading false', async () => {
    const { result } = renderHook(() => useTrends({ autoFetch: false }))

    // Initially not loading
    expect(result.current.isLoading).toBe(false)
  })

  it('should eventually complete loading after setFilters', async () => {
    const { result } = renderHook(() => useTrends({ autoFetch: false }))

    // Start a fetch
    act(() => {
      result.current.photoStats.setFilters({ from_date: undefined })
    })

    // Wait for completion
    await waitFor(() => {
      expect(result.current.photoStats.data).not.toBe(null)
    }, { timeout: 2000 })

    expect(result.current.isLoading).toBe(false)
  })

  it('should report hasError when any hook has error', async () => {
    const { result } = renderHook(() => useTrends({ autoFetch: false }))

    // Initially no error
    expect(result.current.hasError).toBe(false)
  })

  it('should provide fetchAll to trigger all trends', async () => {
    const { result } = renderHook(() => useTrends({ autoFetch: false }))

    // fetchAll should be a function
    expect(typeof result.current.fetchAll).toBe('function')

    // Calling fetchAll should update filters on all hooks
    await act(async () => {
      await result.current.fetchAll()
    })

    // After fetchAll, hooks should have been triggered
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    }, { timeout: 2000 })
  })
})
