/**
 * useNotificationPreferences React hook
 *
 * Manages notification preference state:
 * - Fetch current preferences (GET /preferences)
 * - Update preferences (PUT /preferences) with partial updates
 * - Loading and error states
 *
 * Issue #114 - PWA with Push Notifications (US2)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import * as notificationService from '@/services/notifications'
import type {
  NotificationPreferencesResponse,
  NotificationPreferencesUpdateRequest,
} from '@/contracts/api/notification-api'

// ============================================================================
// Types
// ============================================================================

interface UseNotificationPreferencesReturn {
  /** Current notification preferences */
  preferences: NotificationPreferencesResponse | null
  /** Loading state for fetch or update operations */
  loading: boolean
  /** Error message from the last failed operation */
  error: string | null
  /** Fetch preferences from the server */
  fetchPreferences: () => Promise<void>
  /** Update preferences (partial update) */
  updatePreferences: (
    updates: NotificationPreferencesUpdateRequest
  ) => Promise<NotificationPreferencesResponse | undefined>
}

// ============================================================================
// Hook
// ============================================================================

export const useNotificationPreferences = (
  autoFetch = true
): UseNotificationPreferencesReturn => {
  const [preferences, setPreferences] =
    useState<NotificationPreferencesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Track if component is still mounted
  const mountedRef = useRef(true)
  useEffect(() => {
    return () => {
      mountedRef.current = false
    }
  }, [])

  /**
   * Fetch current preferences from the server
   */
  const fetchPreferences = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await notificationService.getPreferences()
      if (mountedRef.current) {
        setPreferences(data)
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        const errorMessage =
          (err as { userMessage?: string }).userMessage ||
          'Failed to load notification preferences'
        setError(errorMessage)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  /**
   * Update preferences with a partial update
   */
  const updatePreferences = useCallback(
    async (updates: NotificationPreferencesUpdateRequest) => {
      setLoading(true)
      setError(null)
      try {
        const updated = await notificationService.updatePreferences(updates)
        if (mountedRef.current) {
          setPreferences(updated)
        }
        return updated
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            'Failed to update notification preferences'
          setError(errorMessage)
          toast.error('Failed to update preferences', {
            description: errorMessage,
          })
        }
        throw err
      } finally {
        if (mountedRef.current) {
          setLoading(false)
        }
      }
    },
    []
  )

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchPreferences()
    }
  }, [autoFetch, fetchPreferences])

  return {
    preferences,
    loading,
    error,
    fetchPreferences,
    updatePreferences,
  }
}
