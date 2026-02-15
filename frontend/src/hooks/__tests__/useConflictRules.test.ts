/**
 * Tests for useConflictRules hook
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useConflictRules } from '../useConflictRules'
import * as conflictService from '@/services/conflicts'
import type {
  ConflictRulesResponse,
  ConflictRulesUpdateRequest,
} from '@/contracts/api/conflict-api'

// Mock the service
vi.mock('@/services/conflicts')

describe('useConflictRules', () => {
  const mockSettings: ConflictRulesResponse = {
    distance_threshold_miles: 50,
    consecutive_window_days: 3,
    travel_buffer_days: 1,
    colocation_radius_miles: 10,
    performer_ceiling: 5,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(conflictService.getConflictRules).mockResolvedValue(mockSettings)
    vi.mocked(conflictService.updateConflictRules).mockResolvedValue(mockSettings)
  })

  it('should fetch settings on mount by default', async () => {
    const { result } = renderHook(() => useConflictRules())

    expect(result.current.loading).toBe(true)
    expect(result.current.settings).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.settings).toEqual(mockSettings)
    expect(result.current.error).toBe(null)
    expect(conflictService.getConflictRules).toHaveBeenCalledTimes(1)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useConflictRules(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.settings).toBe(null)
    expect(conflictService.getConflictRules).not.toHaveBeenCalled()
  })

  it('should fetch settings manually', async () => {
    const { result } = renderHook(() => useConflictRules(false))

    expect(conflictService.getConflictRules).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.fetchSettings()
    })

    await waitFor(() => {
      expect(result.current.settings).toEqual(mockSettings)
    })

    expect(conflictService.getConflictRules).toHaveBeenCalledTimes(1)
  })

  it('should update settings successfully', async () => {
    const updatedSettings: ConflictRulesResponse = {
      distance_threshold_miles: 100,
      consecutive_window_days: 5,
      travel_buffer_days: 2,
      colocation_radius_miles: 15,
      performer_ceiling: 8,
    }
    vi.mocked(conflictService.updateConflictRules).mockResolvedValue(updatedSettings)

    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: ConflictRulesUpdateRequest = {
      distance_threshold_miles: 100,
      consecutive_window_days: 5,
      travel_buffer_days: 2,
      colocation_radius_miles: 15,
      performer_ceiling: 8,
    }

    await act(async () => {
      await result.current.updateSettings(updateRequest)
    })

    await waitFor(() => {
      expect(result.current.settings).toEqual(updatedSettings)
    })

    expect(conflictService.updateConflictRules).toHaveBeenCalledWith(updateRequest)
  })

  it('should handle fetch error', async () => {
    const error = {
      response: { data: { detail: 'Failed to fetch rules' } },
    }
    vi.mocked(conflictService.getConflictRules).mockRejectedValue(error)

    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch rules')
    expect(result.current.settings).toBe(null)
  })

  it('should handle update error', async () => {
    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const error = {
      response: { data: { detail: 'Failed to update rules' } },
    }
    vi.mocked(conflictService.updateConflictRules).mockRejectedValue(error)

    await act(async () => {
      try {
        await result.current.updateSettings({ distance_threshold_miles: 100 })
        expect.fail('Should have thrown')
      } catch (err: any) {
        expect(err.message).toBe('Failed to update rules')
      }
    })

    expect(result.current.error).toBe('Failed to update rules')
  })

  it('should use fallback error message when detail is missing', async () => {
    const error = { message: 'Network error' }
    vi.mocked(conflictService.getConflictRules).mockRejectedValue(error)

    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
  })

  it('should use default error message when no message available', async () => {
    const error = {}
    vi.mocked(conflictService.getConflictRules).mockRejectedValue(error)

    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch conflict rules')
  })

  it('should clear error on successful fetch after previous error', async () => {
    vi.mocked(conflictService.getConflictRules).mockRejectedValueOnce({ message: 'Error' })

    const { result } = renderHook(() => useConflictRules())

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(conflictService.getConflictRules).mockResolvedValue(mockSettings)

    await act(async () => {
      await result.current.fetchSettings()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.settings).toEqual(mockSettings)
    })
  })

  it('should set loading state during operations', async () => {
    let resolvePromise: (value: ConflictRulesResponse) => void
    const delayedPromise = new Promise<ConflictRulesResponse>((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(conflictService.getConflictRules).mockReturnValue(delayedPromise)

    const { result } = renderHook(() => useConflictRules())

    expect(result.current.loading).toBe(true)

    await act(async () => {
      resolvePromise!(mockSettings)
      await delayedPromise
    })

    expect(result.current.loading).toBe(false)
  })
})
