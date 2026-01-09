/**
 * Integration tests for trend visualization - T134
 *
 * Tests the complete workflow of fetching and displaying trend data
 * across PhotoStats, Photo Pairing, Pipeline Validation, and Display Graph trends.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  usePhotoStatsTrends,
  usePhotoPairingTrends,
  usePipelineValidationTrends,
  useDisplayGraphTrends,
  useTrendSummary,
  useTrends
} from '@/hooks/useTrends'
import { resetMockData } from '../mocks/handlers'

describe('Trend Visualization Integration', () => {
  beforeEach(() => {
    resetMockData()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Full Trend Data Flow', () => {
    it('should fetch all trend types and display aggregated data', async () => {
      // Initialize all trend hooks
      const { result: photoStats } = renderHook(() =>
        usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 })
      )
      const { result: photoPairing } = renderHook(() =>
        usePhotoPairingTrends({ autoFetch: false, debounceMs: 0 })
      )
      const { result: pipelineValidation } = renderHook(() =>
        usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 })
      )
      const { result: displayGraph } = renderHook(() =>
        useDisplayGraphTrends({ autoFetch: false, debounceMs: 0 })
      )
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: false })
      )

      // Fetch all trends (no collection filter = aggregated mode)
      act(() => {
        photoStats.current.setFilters({ from_date: undefined })
        photoPairing.current.setFilters({ from_date: undefined })
        pipelineValidation.current.setFilters({ from_date: undefined })
        displayGraph.current.setFilters({ from_date: undefined })
      })

      await act(async () => {
        await summary.current.refetch()
      })

      // Wait for all to complete - check for data instead of loading state
      await waitFor(() => {
        expect(photoStats.current.data).not.toBe(null)
        expect(photoPairing.current.data).not.toBe(null)
        expect(pipelineValidation.current.data).not.toBe(null)
        expect(displayGraph.current.data).not.toBe(null)
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 5000 })

      // Verify PhotoStats aggregated data
      expect(photoStats.current.data?.mode).toBe('aggregated')
      expect(photoStats.current.data?.data_points).toHaveLength(3)
      expect(photoStats.current.data?.data_points[0].orphaned_images).toBe(10)

      // Verify Photo Pairing aggregated data
      expect(photoPairing.current.data?.mode).toBe('aggregated')
      expect(photoPairing.current.data?.data_points).toHaveLength(3)
      expect(photoPairing.current.data?.data_points[0].group_count).toBe(800)

      // Verify Pipeline Validation aggregated data
      expect(pipelineValidation.current.data?.mode).toBe('aggregated')
      expect(pipelineValidation.current.data?.data_points).toHaveLength(3)
      expect(pipelineValidation.current.data?.data_points[0].overall_consistency_pct).toBe(80)

      // Verify Display Graph data
      expect(displayGraph.current.data?.data_points).toHaveLength(2)
      expect(displayGraph.current.data?.pipelines_included).toHaveLength(1)

      // Verify Summary data
      expect(summary.current.summary?.orphaned_trend).toBe('improving')
      expect(summary.current.summary?.consistency_trend).toBe('stable')
    })

    it('should switch to comparison mode when collection filter is applied', async () => {
      const { result: photoStats } = renderHook(() =>
        usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 })
      )

      // First, fetch aggregated mode
      act(() => {
        photoStats.current.setFilters({ from_date: undefined })
      })

      await waitFor(() => {
        expect(photoStats.current.data?.mode).toBe('aggregated')
      }, { timeout: 2000 })

      // Now apply collection filter for comparison mode
      act(() => {
        photoStats.current.setFilters({ collection_ids: '1' })
      })

      await waitFor(() => {
        expect(photoStats.current.data?.mode).toBe('comparison')
      }, { timeout: 2000 })

      // Should be in comparison mode now
      expect(photoStats.current.data?.collections).toHaveLength(1)
      expect(photoStats.current.data?.collections[0].collection_id).toBe(1)
    })

    it('should support multiple collections in comparison mode', async () => {
      const { result: photoPairing } = renderHook(() =>
        usePhotoPairingTrends({ autoFetch: false, debounceMs: 0 })
      )

      // Apply multiple collection filter
      act(() => {
        photoPairing.current.setFilters({ collection_ids: '1,2' })
      })

      await waitFor(() => {
        expect(photoPairing.current.data).not.toBe(null)
      }, { timeout: 2000 })

      // Should be in comparison mode with 2 collections
      expect(photoPairing.current.data?.mode).toBe('comparison')
      expect(photoPairing.current.data?.collections).toHaveLength(2)

      // Each collection should have camera data
      photoPairing.current.data?.collections.forEach(collection => {
        expect(collection.cameras).toContain('ABC1')
        expect(collection.cameras).toContain('XYZ2')
      })
    })
  })

  describe('Trend Summary Indicators', () => {
    it('should show improving trend for decreasing orphaned files', async () => {
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: true })
      )

      await waitFor(() => {
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 2000 })

      expect(summary.current.summary?.orphaned_trend).toBe('improving')
    })

    it('should show stable trend for consistent pipeline validation', async () => {
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: true })
      )

      await waitFor(() => {
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 2000 })

      expect(summary.current.summary?.consistency_trend).toBe('stable')
    })

    it('should provide last run timestamps for each tool', async () => {
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: true })
      )

      await waitFor(() => {
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 2000 })

      expect(summary.current.summary?.last_photostats).toBe('2025-01-03T10:00:00Z')
      expect(summary.current.summary?.last_photo_pairing).toBe('2025-01-03T11:00:00Z')
      expect(summary.current.summary?.last_pipeline_validation).toBe('2025-01-03T13:00:00Z')
    })

    it('should provide data points available counts', async () => {
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: true })
      )

      await waitFor(() => {
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 2000 })

      expect(summary.current.summary?.data_points_available.photostats).toBe(3)
      expect(summary.current.summary?.data_points_available.photo_pairing).toBe(3)
      expect(summary.current.summary?.data_points_available.pipeline_validation).toBe(3)
    })
  })

  describe('Combined useTrends Hook', () => {
    it('should fetch all trends using the combined hook', async () => {
      const { result } = renderHook(() => useTrends({ autoFetch: false }))

      // Initially all should be empty
      expect(result.current.photoStats.data).toBe(null)
      expect(result.current.photoPairing.data).toBe(null)
      expect(result.current.pipelineValidation.data).toBe(null)
      expect(result.current.summary.summary).toBe(null)

      // Trigger all fetches
      await act(async () => {
        await result.current.fetchAll()
      })

      // Wait for all to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      }, { timeout: 5000 })
    })

    it('should report combined loading state', async () => {
      const { result } = renderHook(() => useTrends({ autoFetch: false }))

      // Initially not loading
      expect(result.current.isLoading).toBe(false)

      // Trigger one fetch
      act(() => {
        result.current.photoStats.setFilters({ from_date: undefined })
      })

      // Wait for data to load
      await waitFor(() => {
        expect(result.current.photoStats.data).not.toBe(null)
      }, { timeout: 2000 })

      // After completion, should not be loading
      expect(result.current.isLoading).toBe(false)
    })

    it('should report combined error state', async () => {
      const { result } = renderHook(() => useTrends({ autoFetch: false }))

      // Initially no error
      expect(result.current.hasError).toBe(false)
    })
  })

  describe('Date Range Filtering', () => {
    it('should apply date range filter to trends', async () => {
      const { result: photoStats } = renderHook(() =>
        usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 })
      )

      act(() => {
        photoStats.current.setFilters({
          from_date: '2025-01-01',
          to_date: '2025-01-31'
        })
      })

      await waitFor(() => {
        expect(photoStats.current.data).not.toBe(null)
      }, { timeout: 2000 })

      // Should have received data (mock doesn't actually filter, but the request is made)
      expect(photoStats.current.filters.from_date).toBe('2025-01-01')
      expect(photoStats.current.filters.to_date).toBe('2025-01-31')
    })
  })

  describe('Pipeline Filter for Validation Trends', () => {
    it('should apply pipeline filter to validation trends', async () => {
      const { result: pipelineValidation } = renderHook(() =>
        usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 })
      )

      act(() => {
        pipelineValidation.current.setFilters({ pipeline_id: 1 })
      })

      await waitFor(() => {
        expect(pipelineValidation.current.data).not.toBe(null)
      }, { timeout: 2000 })

      expect(pipelineValidation.current.filters.pipeline_id).toBe(1)
    })

    it('should apply pipeline version filter', async () => {
      const { result: pipelineValidation } = renderHook(() =>
        usePipelineValidationTrends({ autoFetch: false, debounceMs: 0 })
      )

      act(() => {
        pipelineValidation.current.setFilters({
          pipeline_id: 1,
          pipeline_version: 2
        })
      })

      await waitFor(() => {
        expect(pipelineValidation.current.data).not.toBe(null)
      }, { timeout: 2000 })

      expect(pipelineValidation.current.filters.pipeline_version).toBe(2)
    })
  })

  describe('Display Graph Trends', () => {
    it('should fetch display graph trend data with pipeline information', async () => {
      const { result: displayGraph } = renderHook(() =>
        useDisplayGraphTrends({ autoFetch: false, debounceMs: 0 })
      )

      act(() => {
        displayGraph.current.setFilters({ from_date: undefined })
      })

      await waitFor(() => {
        expect(displayGraph.current.data).not.toBe(null)
      }, { timeout: 2000 })

      expect(displayGraph.current.data?.data_points).toHaveLength(2)

      // Check path counts
      const firstPoint = displayGraph.current.data?.data_points[0]
      expect(firstPoint?.total_paths).toBe(100)
      expect(firstPoint?.valid_paths).toBe(90)
      expect(firstPoint?.black_box_archive_paths).toBe(50)
      expect(firstPoint?.browsable_archive_paths).toBe(40)

      // Check pipelines included
      expect(displayGraph.current.data?.pipelines_included).toHaveLength(1)
      expect(displayGraph.current.data?.pipelines_included[0].pipeline_name).toBe('Standard RAW Workflow')
    })
  })

  describe('Refetch Functionality', () => {
    it('should refetch trends with current filters', async () => {
      const { result: photoStats } = renderHook(() =>
        usePhotoStatsTrends({ autoFetch: false, debounceMs: 0 })
      )

      // Initial fetch
      act(() => {
        photoStats.current.setFilters({ collection_ids: '1' })
      })

      await waitFor(() => {
        expect(photoStats.current.data).not.toBe(null)
      }, { timeout: 2000 })

      const initialMode = photoStats.current.data?.mode

      // Refetch
      await act(async () => {
        await photoStats.current.refetch()
      })

      await waitFor(() => {
        expect(photoStats.current.data).not.toBe(null)
      }, { timeout: 2000 })

      // Data should still be present with same structure
      expect(photoStats.current.data?.mode).toBe(initialMode)
    })

    it('should refetch summary data', async () => {
      const { result: summary } = renderHook(() =>
        useTrendSummary({ autoFetch: false })
      )

      // Initial fetch
      await act(async () => {
        await summary.current.refetch()
      })

      await waitFor(() => {
        expect(summary.current.summary).not.toBe(null)
      }, { timeout: 2000 })

      // Refetch
      await act(async () => {
        await summary.current.refetch()
      })

      expect(summary.current.summary).not.toBe(null)
    })
  })
})
