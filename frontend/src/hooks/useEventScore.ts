/**
 * useEventScore React hook
 *
 * Fetches quality scores for a single event via the scoring API.
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 5, US3)
 */

import { useState, useEffect, useCallback } from 'react'
import { getEventScore } from '../services/conflicts'
import type { EventScoreResponse } from '@/contracts/api/conflict-api'

interface UseEventScoreReturn {
  data: EventScoreResponse | null
  loading: boolean
  error: string | null
  refetch: () => void
}

/**
 * Hook to fetch quality scores for a single event.
 *
 * @param guid - Event GUID to fetch scores for (null/undefined to skip)
 *
 * @example
 * const { data, loading } = useEventScore('evt_abc123')
 * // data.scores.composite → 72
 */
export const useEventScore = (guid: string | null | undefined): UseEventScoreReturn => {
  const [data, setData] = useState<EventScoreResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchScore = useCallback(async () => {
    if (!guid) return
    setLoading(true)
    setError(null)
    try {
      const result = await getEventScore(guid)
      setData(result)
    } catch (err: any) {
      setError(err.userMessage || 'Failed to fetch event score')
    } finally {
      setLoading(false)
    }
  }, [guid])

  useEffect(() => {
    fetchScore()
  }, [fetchScore])

  return { data, loading, error, refetch: fetchScore }
}
