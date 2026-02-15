/**
 * Tests for useNotificationPreferences hook
 *
 * Issue #114 - PWA with Push Notifications (US2)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useNotificationPreferences } from '../useNotificationPreferences'
import * as notificationService from '@/services/notifications'
import type {
  NotificationPreferencesResponse,
  NotificationPreferencesUpdateRequest,
} from '@/contracts/api/notification-api'
import { toast } from 'sonner'

// Mock the service
vi.mock('@/services/notifications')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}))

describe('useNotificationPreferences', () => {
  const mockPreferences: NotificationPreferencesResponse = {
    enabled: true,
    job_failures: true,
    inflection_points: false,
    agent_status: true,
    deadline: true,
    conflict: false,
    retry_warning: false,
    deadline_days_before: 7,
    timezone: 'America/New_York',
    retention_days: 30,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(notificationService.getPreferences).mockResolvedValue(mockPreferences)
    vi.mocked(notificationService.updatePreferences).mockResolvedValue(mockPreferences)
  })

  it('should fetch preferences on mount by default', async () => {
    const { result } = renderHook(() => useNotificationPreferences())

    expect(result.current.loading).toBe(true)
    expect(result.current.preferences).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.preferences).toEqual(mockPreferences)
    expect(result.current.error).toBe(null)
    expect(notificationService.getPreferences).toHaveBeenCalledTimes(1)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useNotificationPreferences(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.preferences).toBe(null)
    expect(notificationService.getPreferences).not.toHaveBeenCalled()
  })

  it('should fetch preferences manually', async () => {
    const { result } = renderHook(() => useNotificationPreferences(false))

    expect(notificationService.getPreferences).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.fetchPreferences()
    })

    await waitFor(() => {
      expect(result.current.preferences).toEqual(mockPreferences)
    })

    expect(notificationService.getPreferences).toHaveBeenCalledTimes(1)
  })

  it('should update preferences successfully', async () => {
    const updatedPreferences: NotificationPreferencesResponse = {
      ...mockPreferences,
      conflict: true,
      inflection_points: true,
    }
    vi.mocked(notificationService.updatePreferences).mockResolvedValue(updatedPreferences)

    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: NotificationPreferencesUpdateRequest = {
      conflict: true,
      inflection_points: true,
    }

    let response: NotificationPreferencesResponse | undefined

    await act(async () => {
      response = await result.current.updatePreferences(updateRequest)
    })

    await waitFor(() => {
      expect(result.current.preferences).toEqual(updatedPreferences)
    })

    expect(response).toEqual(updatedPreferences)
    expect(notificationService.updatePreferences).toHaveBeenCalledWith(updateRequest)
  })

  it('should handle fetch error', async () => {
    const error = { userMessage: 'Failed to fetch preferences' }
    vi.mocked(notificationService.getPreferences).mockRejectedValue(error)

    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch preferences')
    expect(result.current.preferences).toBe(null)
  })

  it('should handle update error', async () => {
    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const error = { userMessage: 'Failed to update preferences' }
    vi.mocked(notificationService.updatePreferences).mockRejectedValue(error)

    await act(async () => {
      try {
        await result.current.updatePreferences({ conflict: true })
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to update preferences')
    expect(toast.error).toHaveBeenCalledWith('Failed to update preferences', {
      description: 'Failed to update preferences',
    })
  })

  it('should use default error message when userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(notificationService.getPreferences).mockRejectedValue(error)

    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load notification preferences')
  })

  it('should clear error on successful fetch after previous error', async () => {
    vi.mocked(notificationService.getPreferences).mockRejectedValueOnce({ userMessage: 'Error' })

    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.error).toBe('Error')
    })

    // Refetch successfully
    vi.mocked(notificationService.getPreferences).mockResolvedValue(mockPreferences)

    await act(async () => {
      await result.current.fetchPreferences()
    })

    await waitFor(() => {
      expect(result.current.error).toBe(null)
      expect(result.current.preferences).toEqual(mockPreferences)
    })
  })

  it('should not update state after unmount', async () => {
    const { result, unmount } = renderHook(() => useNotificationPreferences(false))

    // Start a fetch
    const fetchPromise = act(async () => {
      await result.current.fetchPreferences()
    })

    // Unmount before fetch completes
    unmount()

    // Wait for fetch to complete
    await fetchPromise

    // State should not have been updated (test passes if no errors thrown)
  })

  it('should handle partial updates', async () => {
    const partialUpdate: NotificationPreferencesUpdateRequest = {
      enabled: false,
    }

    const updatedPreferences: NotificationPreferencesResponse = {
      ...mockPreferences,
      enabled: false,
    }

    vi.mocked(notificationService.updatePreferences).mockResolvedValue(updatedPreferences)

    const { result } = renderHook(() => useNotificationPreferences())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.updatePreferences(partialUpdate)
    })

    expect(notificationService.updatePreferences).toHaveBeenCalledWith(partialUpdate)
    expect(result.current.preferences).toEqual(updatedPreferences)
  })

  it('should set loading state during operations', async () => {
    let resolvePromise: (value: NotificationPreferencesResponse) => void
    const delayedPromise = new Promise<NotificationPreferencesResponse>((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(notificationService.getPreferences).mockReturnValue(delayedPromise)

    const { result } = renderHook(() => useNotificationPreferences())

    expect(result.current.loading).toBe(true)

    await act(async () => {
      resolvePromise!(mockPreferences)
      await delayedPromise
    })

    expect(result.current.loading).toBe(false)
  })
})
