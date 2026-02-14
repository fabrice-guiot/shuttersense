/**
 * Scoring Weights Hook
 *
 * Provides functionality to fetch and update event scoring weight settings.
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { useState, useCallback, useEffect } from 'react'
import { getScoringWeights, updateScoringWeights } from '@/services/conflicts'
import type {
  ScoringWeightsResponse,
  ScoringWeightsUpdateRequest,
} from '@/contracts/api/conflict-api'

interface UseScoringWeightsReturn {
  settings: ScoringWeightsResponse | null
  loading: boolean
  error: string | null
  fetchSettings: () => Promise<void>
  updateSettings: (update: ScoringWeightsUpdateRequest) => Promise<void>
}

export function useScoringWeights(autoFetch = true): UseScoringWeightsReturn {
  const [settings, setSettings] = useState<ScoringWeightsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getScoringWeights()
      setSettings(data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to fetch scoring weights'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateSettings = useCallback(async (update: ScoringWeightsUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const data = await updateScoringWeights(update)
      setSettings(data)
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Failed to update scoring weights'
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
