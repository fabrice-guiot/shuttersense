/**
 * Conflict Rules Hook
 *
 * Provides functionality to fetch and update conflict detection rule settings.
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { useState, useCallback, useEffect } from 'react'
import { getConflictRules, updateConflictRules } from '@/services/conflicts'
import type {
  ConflictRulesResponse,
  ConflictRulesUpdateRequest,
} from '@/contracts/api/conflict-api'

interface UseConflictRulesReturn {
  settings: ConflictRulesResponse | null
  loading: boolean
  error: string | null
  fetchSettings: () => Promise<void>
  updateSettings: (update: ConflictRulesUpdateRequest) => Promise<void>
}

export function useConflictRules(autoFetch = true): UseConflictRulesReturn {
  const [settings, setSettings] = useState<ConflictRulesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getConflictRules()
      setSettings(data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to fetch conflict rules'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateSettings = useCallback(async (update: ConflictRulesUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const data = await updateConflictRules(update)
      setSettings(data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to update conflict rules'
      setError(message)
      throw new Error(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      fetchSettings()
    }
  }, [autoFetch, fetchSettings])

  return { settings, loading, error, fetchSettings, updateSettings }
}
