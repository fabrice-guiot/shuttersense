/**
 * useMediaQuery Hook Tests
 *
 * Tests for responsive viewport detection hook.
 * Feature: 016-mobile-calendar-view
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useMediaQuery, useIsMobile } from '@/hooks/useMediaQuery'

// Helper to create a mock MediaQueryList
function createMockMediaQueryList(matches: boolean, query: string): MediaQueryList {
  const listeners: Array<(event: MediaQueryListEvent) => void> = []

  return {
    matches,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: (_event: string, listener: (event: MediaQueryListEvent) => void) => {
      listeners.push(listener)
    },
    removeEventListener: (_event: string, listener: (event: MediaQueryListEvent) => void) => {
      const index = listeners.indexOf(listener)
      if (index > -1) listeners.splice(index, 1)
    },
    dispatchEvent: () => false,
    // Helper to simulate media query change
    _triggerChange: (newMatches: boolean) => {
      listeners.forEach((listener) =>
        listener({ matches: newMatches, media: query } as MediaQueryListEvent)
      )
    },
  } as MediaQueryList & { _triggerChange: (matches: boolean) => void }
}

describe('useMediaQuery', () => {
  let originalMatchMedia: typeof window.matchMedia

  beforeEach(() => {
    originalMatchMedia = window.matchMedia
  })

  afterEach(() => {
    window.matchMedia = originalMatchMedia
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('returns false when media query does not match', () => {
      const mockMql = createMockMediaQueryList(false, '(min-width: 640px)')
      window.matchMedia = vi.fn().mockReturnValue(mockMql)

      const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'))

      expect(result.current).toBe(false)
    })

    it('returns true when media query matches', () => {
      const mockMql = createMockMediaQueryList(true, '(min-width: 640px)')
      window.matchMedia = vi.fn().mockReturnValue(mockMql)

      const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'))

      expect(result.current).toBe(true)
    })

    it('calls matchMedia with the provided query', () => {
      const mockMql = createMockMediaQueryList(false, '(min-width: 768px)')
      window.matchMedia = vi.fn().mockReturnValue(mockMql)

      renderHook(() => useMediaQuery('(min-width: 768px)'))

      expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 768px)')
    })
  })

  describe('Dynamic Changes', () => {
    it('updates when media query match changes', () => {
      const mockMql = createMockMediaQueryList(false, '(min-width: 640px)') as MediaQueryList & {
        _triggerChange: (matches: boolean) => void
      }
      window.matchMedia = vi.fn().mockReturnValue(mockMql)

      const { result } = renderHook(() => useMediaQuery('(min-width: 640px)'))

      expect(result.current).toBe(false)

      // Simulate viewport resize above breakpoint
      act(() => {
        mockMql._triggerChange(true)
      })

      expect(result.current).toBe(true)

      // Simulate viewport resize back below breakpoint
      act(() => {
        mockMql._triggerChange(false)
      })

      expect(result.current).toBe(false)
    })
  })

  describe('Cleanup', () => {
    it('removes event listener on unmount', () => {
      const removeEventListener = vi.fn()
      const mockMql = {
        ...createMockMediaQueryList(false, '(min-width: 640px)'),
        removeEventListener,
      }
      window.matchMedia = vi.fn().mockReturnValue(mockMql)

      const { unmount } = renderHook(() => useMediaQuery('(min-width: 640px)'))

      unmount()

      expect(removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
    })
  })
})

describe('useIsMobile', () => {
  let originalMatchMedia: typeof window.matchMedia

  beforeEach(() => {
    originalMatchMedia = window.matchMedia
  })

  afterEach(() => {
    window.matchMedia = originalMatchMedia
    vi.clearAllMocks()
  })

  it('returns true when viewport is below 640px (mobile)', () => {
    // min-width: 640px does NOT match (we're below 640px)
    const mockMql = createMockMediaQueryList(false, '(min-width: 640px)')
    window.matchMedia = vi.fn().mockReturnValue(mockMql)

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(true) // isMobile = !matches
  })

  it('returns false when viewport is 640px or above (not mobile)', () => {
    // min-width: 640px DOES match (we're at or above 640px)
    const mockMql = createMockMediaQueryList(true, '(min-width: 640px)')
    window.matchMedia = vi.fn().mockReturnValue(mockMql)

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(false) // isMobile = !matches
  })

  it('uses correct breakpoint query', () => {
    const mockMql = createMockMediaQueryList(false, '(min-width: 640px)')
    window.matchMedia = vi.fn().mockReturnValue(mockMql)

    renderHook(() => useIsMobile())

    expect(window.matchMedia).toHaveBeenCalledWith('(min-width: 640px)')
  })
})
