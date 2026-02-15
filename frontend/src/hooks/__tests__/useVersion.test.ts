/**
 * Tests for useVersion hook
 *
 * Fetches application version from backend API with fallback
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useVersion } from '../useVersion'
import api from '@/services/api'

// Mock the API
vi.mock('@/services/api')

describe('useVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Suppress console warnings in tests
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  it('should fetch version on mount', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { version: 'v1.2.3' },
    } as any)

    const { result } = renderHook(() => useVersion())

    expect(result.current.loading).toBe(true)
    expect(result.current.version).toBe('...')

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.version).toBe('v1.2.3')
    expect(result.current.error).toBe(null)
  })

  it('should use fallback version on error', async () => {
    const error = new Error('Network error')
    vi.mocked(api.get).mockRejectedValue(error)

    const { result } = renderHook(() => useVersion())

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.version).toBe('v0.0.0-dev')
    expect(result.current.error).toBe('Failed to fetch version')
  })

  it('should pass correct timeout to API', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { version: 'v1.0.0' },
    } as any)

    renderHook(() => useVersion())

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/version', { timeout: 5000 })
    })
  })

  it('should fetch development version format', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { version: 'v1.2.3-dev.5+a1b2c3d' },
    } as any)

    const { result } = renderHook(() => useVersion())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.version).toBe('v1.2.3-dev.5+a1b2c3d')
  })
})
