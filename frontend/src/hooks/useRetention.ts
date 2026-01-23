/**
 * Retention Settings Hook
 *
 * Provides functionality to fetch and update result retention configuration.
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import type {
  RetentionSettingsResponse,
  RetentionSettingsUpdate
} from '@/contracts/api/retention-api'

// ============================================================================
// Types
// ============================================================================

interface UseRetentionReturn {
  /** Current retention settings */
  settings: RetentionSettingsResponse | null
  /** Loading state */
  loading: boolean
  /** Error message */
  error: string | null
  /** Fetch current retention settings */
  fetchSettings: () => Promise<void>
  /** Update retention settings */
  updateSettings: (update: RetentionSettingsUpdate) => Promise<void>
  /** Clear error state */
  clearError: () => void
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for managing retention settings.
 *
 * @param autoFetch - Whether to fetch settings automatically on mount (default: true)
 * @returns Retention settings state and actions
 *
 * @example
 * ```tsx
 * const { settings, loading, updateSettings } = useRetention()
 *
 * // Update a single setting
 * await updateSettings({ job_completed_days: 7 })
 * ```
 */
export function useRetention(autoFetch = true): UseRetentionReturn {
  const [settings, setSettings] = useState<RetentionSettingsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.get<RetentionSettingsResponse>('/api/config/retention')
      setSettings(response.data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to fetch retention settings'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateSettings = useCallback(async (update: RetentionSettingsUpdate) => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.put<RetentionSettingsResponse>(
        '/api/config/retention',
        update
      )
      setSettings(response.data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to update retention settings'
      setError(message)
      throw new Error(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchSettings()
    }
  }, [autoFetch, fetchSettings])

  return {
    settings,
    loading,
    error,
    fetchSettings,
    updateSettings,
    clearError
  }
}

export default useRetention
