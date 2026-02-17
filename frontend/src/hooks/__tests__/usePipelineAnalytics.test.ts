/**
 * Tests for usePipelineAnalytics hook
 *
 * Manages pipeline flow analytics state: fetching analytics data from the API,
 * tracking loading/error/enabled states, and controlling flow overlay visibility.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { AxiosError, AxiosHeaders } from 'axios'
import type { PipelineFlowAnalyticsResponse } from '@/contracts/api/pipelines-api'
import { usePipelineAnalytics } from '../usePipelineAnalytics'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('@/services/pipelines', () => ({
  getFlowAnalytics: vi.fn(),
}))

import { getFlowAnalytics } from '@/services/pipelines'

const mockGetFlowAnalytics = vi.mocked(getFlowAnalytics)

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const sampleAnalytics: PipelineFlowAnalyticsResponse = {
  pipeline_guid: 'pip_test123',
  pipeline_version: 3,
  result_guid: 'res_abc456',
  result_created_at: '2026-02-15T10:30:00Z',
  result_status: 'COMPLETED',
  collection_guid: 'col_test789',
  collection_name: 'Test Collection',
  completed_at: '2026-02-15T10:35:00Z',
  files_scanned: 1204,
  total_records: 500,
  nodes: [
    { node_id: 'capture', record_count: 500, percentage: 100 },
    { node_id: 'raw', record_count: 480, percentage: 96 },
    { node_id: 'done', record_count: 480, percentage: 96 },
  ],
  edges: [
    { from_node: 'capture', to_node: 'raw', record_count: 480, percentage: 96 },
    { from_node: 'raw', to_node: 'done', record_count: 480, percentage: 100 },
  ],
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('usePipelineAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ========================================================================
  // 1. Fetches analytics on mount when pipelineGuid is provided
  // ========================================================================

  it('fetches analytics on mount when pipelineGuid is provided', async () => {
    mockGetFlowAnalytics.mockResolvedValue(sampleAnalytics)

    renderHook(() => usePipelineAnalytics('pip_test123'))

    await waitFor(() => {
      expect(mockGetFlowAnalytics).toHaveBeenCalledWith('pip_test123', undefined)
    })
  })

  // ========================================================================
  // 2. Does not fetch when pipelineGuid is null
  // ========================================================================

  it('does not fetch when pipelineGuid is null', async () => {
    renderHook(() => usePipelineAnalytics(null))

    // Give the effect time to run (or not)
    await waitFor(() => {
      expect(mockGetFlowAnalytics).not.toHaveBeenCalled()
    })
  })

  // ========================================================================
  // 3. Sets enabled=true and populates analytics when fetch succeeds
  // ========================================================================

  it('sets enabled=true and populates analytics when fetch succeeds', async () => {
    mockGetFlowAnalytics.mockResolvedValue(sampleAnalytics)

    const { result } = renderHook(() => usePipelineAnalytics('pip_test123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.analytics).toEqual(sampleAnalytics)
    expect(result.current.enabled).toBe(true)
    expect(result.current.error).toBeNull()
  })

  // ========================================================================
  // 4. Sets enabled=false when fetch returns 404
  // ========================================================================

  it('sets enabled=false when fetch returns 404', async () => {
    const axiosError = new AxiosError('Not Found', '404', undefined, undefined, {
      status: 404,
      statusText: 'Not Found',
      data: {},
      headers: {},
      config: { headers: new AxiosHeaders() },
    })

    mockGetFlowAnalytics.mockRejectedValue(axiosError)

    const { result } = renderHook(() => usePipelineAnalytics('pip_test123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.enabled).toBe(false)
    expect(result.current.analytics).toBeNull()
    expect(result.current.error).toBeNull()
  })

  // ========================================================================
  // 5. Passes resultGuid to getFlowAnalytics when provided
  // ========================================================================

  it('passes resultGuid to getFlowAnalytics when provided', async () => {
    mockGetFlowAnalytics.mockResolvedValue(sampleAnalytics)

    renderHook(() => usePipelineAnalytics('pip_test123', 'res_abc456'))

    await waitFor(() => {
      expect(mockGetFlowAnalytics).toHaveBeenCalledWith('pip_test123', 'res_abc456')
    })
  })

  // ========================================================================
  // 6. loading is true during fetch, false after
  // ========================================================================

  it('loading is true during fetch, false after', async () => {
    let resolvePromise: (value: PipelineFlowAnalyticsResponse) => void
    const pendingPromise = new Promise<PipelineFlowAnalyticsResponse>((resolve) => {
      resolvePromise = resolve
    })

    mockGetFlowAnalytics.mockReturnValue(pendingPromise)

    const { result } = renderHook(() => usePipelineAnalytics('pip_test123'))

    // loading should be true while the promise is pending
    await waitFor(() => {
      expect(result.current.loading).toBe(true)
    })

    // Resolve the promise
    await act(async () => {
      resolvePromise!(sampleAnalytics)
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
  })

  // ========================================================================
  // 7. error is set when fetch fails with non-404 error
  // ========================================================================

  it('error is set when fetch fails with non-404 error', async () => {
    const genericError = new Error('Network error')

    mockGetFlowAnalytics.mockRejectedValue(genericError)

    const { result } = renderHook(() => usePipelineAnalytics('pip_test123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.analytics).toBeNull()
  })

  // ========================================================================
  // 8. refetch re-triggers the API call
  // ========================================================================

  it('refetch re-triggers the API call', async () => {
    mockGetFlowAnalytics.mockResolvedValue(sampleAnalytics)

    const { result } = renderHook(() => usePipelineAnalytics('pip_test123'))

    // Wait for initial fetch to complete
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(mockGetFlowAnalytics).toHaveBeenCalledTimes(1)

    // Trigger refetch
    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(mockGetFlowAnalytics).toHaveBeenCalledTimes(2)
    })
  })
})
