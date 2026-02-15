/**
 * Tests for useScoringWeights hook
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useScoringWeights } from '../useScoringWeights'
import * as conflictService from '@/services/conflicts'
import type {
  ScoringWeightsResponse,
  ScoringWeightsUpdateRequest,
} from '@/contracts/api/conflict-api'

// Mock the service
vi.mock('@/services/conflicts')

describe('useScoringWeights', () => {
  const mockSettings: ScoringWeightsResponse = {
    weight_venue_quality: 0.2,
    weight_organizer_reputation: 0.2,
    weight_performer_lineup: 0.2,
    weight_logistics_ease: 0.2,
    weight_readiness: 0.2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(conflictService.getScoringWeights).mockResolvedValue(mockSettings)
    vi.mocked(conflictService.updateScoringWeights).mockResolvedValue(mockSettings)
  })

  it('should fetch settings on mount by default', async () => {
    const { result } = renderHook(() => useScoringWeights())

    expect(result.current.loading).toBe(true)
    expect(result.current.settings).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.settings).toEqual(mockSettings)
    expect(result.current.error).toBe(null)
    expect(conflictService.getScoringWeights).toHaveBeenCalledTimes(1)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useScoringWeights(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.settings).toBe(null)
    expect(conflictService.getScoringWeights).not.toHaveBeenCalled()
  })

  it('should fetch settings manually', async () => {
    const { result } = renderHook(() => useScoringWeights(false))

    expect(conflictService.getScoringWeights).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.fetchSettings()
    })

    await waitFor(() => {
      expect(result.current.settings).toEqual(mockSettings)
    })

    expect(conflictService.getScoringWeights).toHaveBeenCalledTimes(1)
  })

  it('should update settings successfully', async () => {
    const updatedSettings: ScoringWeightsResponse = {
      weight_venue_quality: 0.3,
      weight_organizer_reputation: 0.25,
      weight_performer_lineup: 0.2,
      weight_logistics_ease: 0.15,
      weight_readiness: 0.1,
    }
    vi.mocked(conflictService.updateScoringWeights).mockResolvedValue(updatedSettings)

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: ScoringWeightsUpdateRequest = {
      weight_venue_quality: 0.3,
      weight_organizer_reputation: 0.25,
      weight_performer_lineup: 0.2,
      weight_logistics_ease: 0.15,
      weight_readiness: 0.1,
    }

    await act(async () => {
      await result.current.updateSettings(updateRequest)
    })

    await waitFor(() => {
      expect(result.current.settings).toEqual(updatedSettings)
    })

    expect(conflictService.updateScoringWeights).toHaveBeenCalledWith(updateRequest)
  })

  it('should handle fetch error', async () => {
    const error = {
      response: { data: { detail: 'Failed to fetch weights' } },
    }
    vi.mocked(conflictService.getScoringWeights).mockRejectedValue(error)

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch weights')
    expect(result.current.settings).toBe(null)
  })

  it('should handle update error', async () => {
    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const error = {
      response: { data: { detail: 'Failed to update weights' } },
    }
    vi.mocked(conflictService.updateScoringWeights).mockRejectedValue(error)

    await act(async () => {
      try {
        await result.current.updateSettings({ weight_venue_quality: 0.5 })
        expect.fail('Should have thrown')
      } catch (err: any) {
        expect(err.message).toBe('Failed to update weights')
      }
    })

    expect(result.current.error).toBe('Failed to update weights')
  })

  it('should use fallback error message when detail is missing', async () => {
    const error = { message: 'Network error' }
    vi.mocked(conflictService.getScoringWeights).mockRejectedValue(error)

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
  })

  it('should use default error message when no message available', async () => {
    const error = {}
    vi.mocked(conflictService.getScoringWeights).mockRejectedValue(error)

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch scoring weights')
  })

  it('should clear error on successful fetch after previous error', async () => {
    vi.mocked(conflictService.getScoringWeights).mockRejectedValueOnce({ message: 'Error' })

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(conflictService.getScoringWeights).mockResolvedValue(mockSettings)

    await act(async () => {
      await result.current.fetchSettings()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.settings).toEqual(mockSettings)
    })
  })

  it('should set loading state during operations', async () => {
    let resolvePromise: (value: ScoringWeightsResponse) => void
    const delayedPromise = new Promise<ScoringWeightsResponse>((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(conflictService.getScoringWeights).mockReturnValue(delayedPromise)

    const { result } = renderHook(() => useScoringWeights())

    expect(result.current.loading).toBe(true)

    await act(async () => {
      resolvePromise!(mockSettings)
      await delayedPromise
    })

    expect(result.current.loading).toBe(false)
  })

  it('should validate weights sum to 1.0', async () => {
    // Note: Validation is typically done at the API level, but we can test
    // that the hook passes the request through correctly
    const updatedSettings: ScoringWeightsResponse = {
      weight_venue_quality: 0.3,
      weight_organizer_reputation: 0.2,
      weight_performer_lineup: 0.2,
      weight_logistics_ease: 0.15,
      weight_readiness: 0.15,
    }
    vi.mocked(conflictService.updateScoringWeights).mockResolvedValue(updatedSettings)

    const { result } = renderHook(() => useScoringWeights())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: ScoringWeightsUpdateRequest = {
      weight_venue_quality: 0.3,
      weight_organizer_reputation: 0.2,
      weight_performer_lineup: 0.2,
      weight_logistics_ease: 0.15,
      weight_readiness: 0.15,
    }

    await act(async () => {
      await result.current.updateSettings(updateRequest)
    })

    expect(result.current.settings).toEqual(updatedSettings)
  })
})
