/**
 * Tests for useRetention hook.
 *
 * Tests cover:
 * - Fetching retention settings
 * - Updating retention settings
 * - Error handling
 * - Loading states
 *
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { describe, test, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { useRetention } from '../useRetention'

// Helper to wait for hook updates
const waitForHookUpdate = async () => {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('useRetention', () => {
  describe('fetching settings', () => {
    test('fetches settings automatically on mount', async () => {
      const { result } = renderHook(() => useRetention())

      // Initially loading
      expect(result.current.loading).toBe(true)
      expect(result.current.settings).toBe(null)

      // Wait for fetch to complete
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should have settings
      expect(result.current.settings).not.toBe(null)
      expect(result.current.settings?.job_completed_days).toBe(2)
      expect(result.current.settings?.job_failed_days).toBe(7)
      expect(result.current.settings?.result_completed_days).toBe(0)
      expect(result.current.settings?.preserve_per_collection).toBe(1)
    })

    test('does not auto-fetch when autoFetch is false', async () => {
      const { result } = renderHook(() => useRetention(false))

      await waitForHookUpdate()

      // Should not have loaded settings
      expect(result.current.loading).toBe(false)
      expect(result.current.settings).toBe(null)
    })

    test('handles fetch error', async () => {
      // Override handler to return error
      server.use(
        http.get('/api/config/retention', () => {
          return HttpResponse.json(
            { detail: 'Database connection failed' },
            { status: 500 }
          )
        })
      )

      const { result } = renderHook(() => useRetention())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.error).toBe('Database connection failed')
      expect(result.current.settings).toBe(null)
    })

    test('can manually fetch settings', async () => {
      const { result } = renderHook(() => useRetention(false))

      // Verify not auto-fetched
      expect(result.current.settings).toBe(null)

      // Manually fetch and wait for result
      await act(async () => {
        result.current.fetchSettings()
      })

      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify the values
      expect(result.current.settings).not.toBe(null)
      expect(result.current.settings?.job_completed_days).toBe(2)
    })
  })

  describe('updating settings', () => {
    test('updates a single setting', async () => {
      const { result } = renderHook(() => useRetention())

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Update job_completed_days
      await act(async () => {
        await result.current.updateSettings({ job_completed_days: 30 })
      })

      expect(result.current.settings?.job_completed_days).toBe(30)
    })

    test('updates multiple settings', async () => {
      const { result } = renderHook(() => useRetention())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await act(async () => {
        await result.current.updateSettings({
          job_completed_days: 14,
          job_failed_days: 30,
          preserve_per_collection: 3
        })
      })

      expect(result.current.settings?.job_completed_days).toBe(14)
      expect(result.current.settings?.job_failed_days).toBe(30)
      expect(result.current.settings?.preserve_per_collection).toBe(3)
    })

    test('handles update error', async () => {
      // Override handler BEFORE rendering
      server.use(
        http.put('/api/config/retention', () => {
          return HttpResponse.json(
            { detail: 'Validation failed' },
            { status: 400 }
          )
        })
      )

      const { result } = renderHook(() => useRetention())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should throw error
      let errorThrown = false
      try {
        await act(async () => {
          await result.current.updateSettings({ job_completed_days: 30 })
        })
      } catch (e) {
        errorThrown = true
        expect((e as Error).message).toBe('Validation failed')
      }
      expect(errorThrown).toBe(true)
    })

    test('rejects invalid values via API validation', async () => {
      server.use(
        http.put('/api/config/retention', async ({ request }) => {
          const data = await request.json() as Record<string, number>
          if (data.job_completed_days === 15) {
            return HttpResponse.json(
              { detail: 'Invalid job_completed_days value' },
              { status: 422 }
            )
          }
          return HttpResponse.json({ ...data })
        })
      )

      const { result } = renderHook(() => useRetention())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      let errorThrown = false
      try {
        await act(async () => {
          await result.current.updateSettings({ job_completed_days: 15 as any })
        })
      } catch (e) {
        errorThrown = true
        expect((e as Error).message).toBe('Invalid job_completed_days value')
      }
      expect(errorThrown).toBe(true)
    })
  })

  describe('error handling', () => {
    test('clearError clears error state', async () => {
      server.use(
        http.get('/api/config/retention', () => {
          return HttpResponse.json(
            { detail: 'Test error' },
            { status: 500 }
          )
        })
      )

      const { result } = renderHook(() => useRetention())

      await waitFor(() => {
        expect(result.current.error).toBe('Test error')
      })

      act(() => {
        result.current.clearError()
      })

      expect(result.current.error).toBe(null)
    })
  })
})
