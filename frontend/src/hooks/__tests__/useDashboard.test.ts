/**
 * Tests for useDashboard hook
 *
 * Provides dashboard-specific data fetching
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useRecentResults, useEventDashboardStats } from '../useDashboard'
import * as resultsService from '@/services/results'
import * as eventsService from '@/services/events'
import type { AnalysisResultSummary } from '@/contracts/api/results-api'
import type { EventDashboardStatsResponse } from '@/contracts/api/event-api'

// Mock the services
vi.mock('@/services/results')
vi.mock('@/services/events')

describe('useRecentResults', () => {
  const mockResults: AnalysisResultSummary[] = [
    {
      guid: 'res_01hgw2bbg00000000000000001',
      tool: 'photostats',
      collection_guid: 'col_01hgw2bbg00000000000000001',
      collection_name: 'Summer Photos',
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      connector_guid: null,
      connector_name: null,
      status: 'COMPLETED',
      started_at: '2026-02-14T10:00:00Z',
      completed_at: '2026-02-14T10:05:00Z',
      duration_seconds: 300,
      files_scanned: 1000,
      issues_found: 5,
      has_report: true,
      input_state_hash: null,
      no_change_copy: false,
    },
    {
      guid: 'res_01hgw2bbg00000000000000002',
      tool: 'photo_pairing',
      collection_guid: 'col_01hgw2bbg00000000000000002',
      collection_name: 'Wedding Photos',
      pipeline_guid: null,
      pipeline_version: null,
      pipeline_name: null,
      connector_guid: null,
      connector_name: null,
      status: 'COMPLETED',
      started_at: '2026-02-13T15:00:00Z',
      completed_at: '2026-02-13T15:10:00Z',
      duration_seconds: 600,
      files_scanned: 500,
      issues_found: 0,
      has_report: true,
      input_state_hash: null,
      no_change_copy: false,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(resultsService.listResults).mockResolvedValue({
      items: mockResults,
      total: 2,
      limit: 5,
      offset: 0,
    })
  })

  it('should fetch recent results on mount', async () => {
    const { result } = renderHook(() => useRecentResults())

    expect(result.current.loading).toBe(true)
    expect(result.current.results).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.results).toEqual(mockResults)
    expect(result.current.error).toBe(null)
    expect(resultsService.listResults).toHaveBeenCalledWith({
      limit: 5,
      offset: 0,
      sort_by: 'created_at',
      sort_order: 'desc',
    })
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useRecentResults(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.results).toEqual([])
    expect(resultsService.listResults).not.toHaveBeenCalled()
  })

  it('should refetch results on demand', async () => {
    const { result } = renderHook(() => useRecentResults())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(resultsService.listResults).toHaveBeenCalledTimes(1)

    await act(async () => {
      await result.current.refetch()
    })

    expect(resultsService.listResults).toHaveBeenCalledTimes(2)
  })

  it('should handle fetch error', async () => {
    const error = { userMessage: 'Failed to load results' }
    vi.mocked(resultsService.listResults).mockRejectedValue(error)

    const { result } = renderHook(() => useRecentResults())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load results')
    expect(result.current.results).toEqual([])
  })

  it('should use default error message when userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(resultsService.listResults).mockRejectedValue(error)

    const { result } = renderHook(() => useRecentResults())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load recent results')
  })

  it('should clear error on successful refetch', async () => {
    vi.mocked(resultsService.listResults).mockRejectedValueOnce({ userMessage: 'Error' })

    const { result } = renderHook(() => useRecentResults())

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(resultsService.listResults).mockResolvedValue({
      items: mockResults,
      total: 2,
      limit: 5,
      offset: 0,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.results).toEqual(mockResults)
    })
  })
})

describe('useEventDashboardStats', () => {
  const mockStats: EventDashboardStatsResponse = {
    upcoming_30d_count: 5,
    needs_tickets_count: 3,
    needs_pto_count: 0,
    needs_travel_count: 0,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventsService.getEventDashboardStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useEventDashboardStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
    expect(eventsService.getEventDashboardStats).toHaveBeenCalledTimes(1)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useEventDashboardStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(eventsService.getEventDashboardStats).not.toHaveBeenCalled()
  })

  it('should refetch stats on demand', async () => {
    const { result } = renderHook(() => useEventDashboardStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(eventsService.getEventDashboardStats).toHaveBeenCalledTimes(1)

    await act(async () => {
      await result.current.refetch()
    })

    expect(eventsService.getEventDashboardStats).toHaveBeenCalledTimes(2)
  })

  it('should handle fetch error', async () => {
    const error = { userMessage: 'Failed to load stats' }
    vi.mocked(eventsService.getEventDashboardStats).mockRejectedValue(error)

    const { result } = renderHook(() => useEventDashboardStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load stats')
    expect(result.current.stats).toBe(null)
  })

  it('should use default error message when userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(eventsService.getEventDashboardStats).mockRejectedValue(error)

    const { result } = renderHook(() => useEventDashboardStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load event dashboard stats')
  })

  it('should clear error on successful refetch', async () => {
    vi.mocked(eventsService.getEventDashboardStats).mockRejectedValueOnce({ userMessage: 'Error' })

    const { result } = renderHook(() => useEventDashboardStats())

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(eventsService.getEventDashboardStats).mockResolvedValue(mockStats)

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.stats).toEqual(mockStats)
    })
  })

  it('should handle zero counts', async () => {
    const emptyStats: EventDashboardStatsResponse = {
      upcoming_30d_count: 0,
      needs_tickets_count: 0,
      needs_pto_count: 0,
      needs_travel_count: 0,
    }
    vi.mocked(eventsService.getEventDashboardStats).mockResolvedValue(emptyStats)

    const { result } = renderHook(() => useEventDashboardStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(emptyStats)
  })
})
