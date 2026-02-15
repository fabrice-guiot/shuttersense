/**
 * Tests for useResolveConflict hook
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 4, US2)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useResolveConflict } from '../useResolveConflict'
import * as conflictService from '@/services/conflicts'
import type {
  ConflictResolveRequest,
  ConflictResolveResponse,
} from '@/contracts/api/conflict-api'

// Mock the service
vi.mock('@/services/conflicts')

describe('useResolveConflict', () => {
  const mockRequest: ConflictResolveRequest = {
    group_id: 'cg_1',
    decisions: [
      {
        event_guid: 'evt_01hgw2bbg00000000000000001',
        attendance: 'planned',
      },
      {
        event_guid: 'evt_01hgw2bbg00000000000000002',
        attendance: 'skipped',
      },
    ],
  }

  const mockResponse: ConflictResolveResponse = {
    success: true,
    updated_count: 2,
    message: 'Conflict resolved successfully',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(conflictService.resolveConflict).mockResolvedValue(mockResponse)
  })

  it('should resolve conflict successfully', async () => {
    const { result } = renderHook(() => useResolveConflict())

    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)

    let response: ConflictResolveResponse | undefined

    await act(async () => {
      response = await result.current.resolve(mockRequest)
    })

    expect(response).toEqual(mockResponse)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
    expect(conflictService.resolveConflict).toHaveBeenCalledWith(mockRequest)
  })

  it('should call onSuccess callback after successful resolution', async () => {
    const onSuccess = vi.fn()
    const { result } = renderHook(() => useResolveConflict({ onSuccess }))

    await act(async () => {
      await result.current.resolve(mockRequest)
    })

    expect(onSuccess).toHaveBeenCalledTimes(1)
  })

  it('should not call onSuccess on error', async () => {
    const onSuccess = vi.fn()
    const error = { userMessage: 'Resolution failed' }
    vi.mocked(conflictService.resolveConflict).mockRejectedValue(error)

    const { result } = renderHook(() => useResolveConflict({ onSuccess }))

    await act(async () => {
      try {
        await result.current.resolve(mockRequest)
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('should handle resolve error', async () => {
    const error = { userMessage: 'Failed to resolve conflict' }
    vi.mocked(conflictService.resolveConflict).mockRejectedValue(error)

    const { result } = renderHook(() => useResolveConflict())

    await act(async () => {
      try {
        await result.current.resolve(mockRequest)
        expect.unreachable('Should have thrown')
      } catch (err: any) {
        expect(err.userMessage).toBe('Failed to resolve conflict')
      }
    })

    expect(result.current.error).toBe('Failed to resolve conflict')
    expect(result.current.loading).toBe(false)
  })

  it('should use default error message when userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(conflictService.resolveConflict).mockRejectedValue(error)

    const { result } = renderHook(() => useResolveConflict())

    await act(async () => {
      try {
        await result.current.resolve(mockRequest)
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to resolve conflict')
  })

  it('should set loading state during resolution', async () => {
    let resolvePromise: (value: ConflictResolveResponse) => void
    const delayedPromise = new Promise<ConflictResolveResponse>((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(conflictService.resolveConflict).mockReturnValue(delayedPromise)

    const { result } = renderHook(() => useResolveConflict())

    expect(result.current.loading).toBe(false)

    act(() => {
      result.current.resolve(mockRequest)
    })

    expect(result.current.loading).toBe(true)

    await act(async () => {
      resolvePromise!(mockResponse)
      await delayedPromise
    })

    expect(result.current.loading).toBe(false)
  })

  it('should clear error on successful resolve after previous error', async () => {
    vi.mocked(conflictService.resolveConflict).mockRejectedValueOnce({ userMessage: 'Error' })

    const { result } = renderHook(() => useResolveConflict())

    // First call fails
    await act(async () => {
      try {
        await result.current.resolve(mockRequest)
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Error')

    // Second call succeeds
    vi.mocked(conflictService.resolveConflict).mockResolvedValue(mockResponse)

    await act(async () => {
      await result.current.resolve(mockRequest)
    })

    expect(result.current.error).toBe(null)
  })
})
