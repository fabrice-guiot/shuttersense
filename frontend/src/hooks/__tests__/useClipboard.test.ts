/**
 * Tests for useClipboard hook
 *
 * Provides clipboard copy functionality with success/error state tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useClipboard } from '../useClipboard'

describe('useClipboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Suppress console errors in tests
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should copy text to clipboard successfully', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    })

    const { result } = renderHook(() => useClipboard())

    expect(result.current.copied).toBe(false)
    expect(result.current.error).toBe(null)

    let success: boolean = false
    await act(async () => {
      success = await result.current.copy('test text')
    })

    expect(success).toBe(true)
    expect(result.current.copied).toBe(true)
    expect(result.current.error).toBe(null)
    expect(mockWriteText).toHaveBeenCalledWith('test text')
  })

  it('should reset copied state after delay', async () => {
    vi.useFakeTimers()

    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    })

    const { result } = renderHook(() => useClipboard({ resetDelay: 1000 }))

    await act(async () => {
      await result.current.copy('test text')
    })

    expect(result.current.copied).toBe(true)

    // Fast-forward time and wait for state update
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    expect(result.current.copied).toBe(false)

    vi.useRealTimers()
  })

  it('should handle copy error', async () => {
    const mockError = new Error('Permission denied')
    const mockWriteText = vi.fn().mockRejectedValue(mockError)
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    })

    const { result } = renderHook(() => useClipboard())

    let success: boolean = true
    await act(async () => {
      success = await result.current.copy('test text')
    })

    expect(success).toBe(false)
    expect(result.current.copied).toBe(false)
    expect(result.current.error).toBe('Permission denied')
  })

  it('should use fallback for older browsers', async () => {
    // Mock document.execCommand for fallback
    const mockExecCommand = vi.fn().mockReturnValue(true)
    document.execCommand = mockExecCommand

    // Remove modern clipboard API
    Object.assign(navigator, {
      clipboard: undefined,
    })

    const { result } = renderHook(() => useClipboard())

    let success: boolean = false
    await act(async () => {
      success = await result.current.copy('fallback text')
    })

    expect(success).toBe(true)
    expect(result.current.copied).toBe(true)
    expect(mockExecCommand).toHaveBeenCalledWith('copy')
  })

  it('should reset error state on new copy attempt', async () => {
    const mockWriteText = vi.fn()
      .mockRejectedValueOnce(new Error('First error'))
      .mockResolvedValueOnce(undefined)

    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    })

    const { result } = renderHook(() => useClipboard())

    // First attempt fails
    await act(async () => {
      await result.current.copy('test')
    })

    expect(result.current.error).toBe('First error')

    // Second attempt succeeds
    await act(async () => {
      await result.current.copy('test')
    })

    expect(result.current.error).toBe(null)
    expect(result.current.copied).toBe(true)
  })

  it('should use custom reset delay', async () => {
    vi.useFakeTimers()

    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
      },
    })

    const { result } = renderHook(() => useClipboard({ resetDelay: 3000 }))

    await act(async () => {
      await result.current.copy('test')
    })

    expect(result.current.copied).toBe(true)

    // Should still be copied after 2 seconds
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    expect(result.current.copied).toBe(true)

    // Should be reset after 3 seconds
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })

    expect(result.current.copied).toBe(false)

    vi.useRealTimers()
  })
})
