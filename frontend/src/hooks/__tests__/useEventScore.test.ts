/**
 * Tests for useEventScore hook
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 5, US3)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useEventScore } from '../useEventScore'
import * as conflictService from '@/services/conflicts'
import type { EventScoreResponse } from '@/contracts/api/conflict-api'

// Mock the service
vi.mock('@/services/conflicts')

describe('useEventScore', () => {
  const mockScore: EventScoreResponse = {
    guid: 'evt_01hgw2bbg00000000000000001',
    title: 'Test Event',
    event_date: '2026-03-15',
    scores: {
      composite: 72,
      venue_quality: 80,
      organizer_reputation: 70,
      performer_lineup: 65,
      logistics_ease: 75,
      readiness: 68,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(conflictService.getEventScore).mockResolvedValue(mockScore)
  })

  it('should fetch score on mount', async () => {
    const { result } = renderHook(() => useEventScore('evt_01hgw2bbg00000000000000001'))

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual(mockScore)
    expect(result.current.error).toBe(null)
    expect(conflictService.getEventScore).toHaveBeenCalledWith('evt_01hgw2bbg00000000000000001')
  })

  it('should skip fetch when guid is null', async () => {
    const { result } = renderHook(() => useEventScore(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBe(null)
    expect(conflictService.getEventScore).not.toHaveBeenCalled()
  })

  it('should skip fetch when guid is undefined', async () => {
    const { result } = renderHook(() => useEventScore(undefined))

    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBe(null)
    expect(conflictService.getEventScore).not.toHaveBeenCalled()
  })

  it('should refetch when guid changes', async () => {
    const { result, rerender } = renderHook(
      ({ guid }) => useEventScore(guid),
      { initialProps: { guid: 'evt_01hgw2bbg00000000000000001' } }
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(conflictService.getEventScore).toHaveBeenCalledTimes(1)

    // Change guid
    const newScore: EventScoreResponse = {
      ...mockScore,
      guid: 'evt_01hgw2bbg00000000000000002',
    }
    vi.mocked(conflictService.getEventScore).mockResolvedValue(newScore)

    rerender({ guid: 'evt_01hgw2bbg00000000000000002' })

    await waitFor(() => {
      expect(conflictService.getEventScore).toHaveBeenCalledTimes(2)
    })

    expect(conflictService.getEventScore).toHaveBeenCalledWith('evt_01hgw2bbg00000000000000002')
  })

  it('should handle fetch error', async () => {
    const error = { userMessage: 'Event not found' }
    vi.mocked(conflictService.getEventScore).mockRejectedValue(error)

    const { result } = renderHook(() => useEventScore('evt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Event not found')
    expect(result.current.data).toBe(null)
  })

  it('should use default error message when userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(conflictService.getEventScore).mockRejectedValue(error)

    const { result } = renderHook(() => useEventScore('evt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch event score')
  })

  it('should refetch score on demand', async () => {
    const { result } = renderHook(() => useEventScore('evt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(conflictService.getEventScore).toHaveBeenCalledTimes(1)

    // Refetch
    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(conflictService.getEventScore).toHaveBeenCalledTimes(2)
    })
  })

  it('should clear error on successful refetch', async () => {
    vi.mocked(conflictService.getEventScore).mockRejectedValueOnce({ userMessage: 'Error' })

    const { result } = renderHook(() => useEventScore('evt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(conflictService.getEventScore).mockResolvedValue(mockScore)

    await act(async () => {
      result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.data).toEqual(mockScore)
    })
  })
})
