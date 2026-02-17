import { useCallback, useEffect, useState } from 'react'
import type { PipelineFlowAnalyticsResponse } from '@/contracts/api/pipelines-api'
import { getFlowAnalytics } from '@/services/pipelines'
import { AxiosError } from 'axios'

interface UsePipelineAnalyticsReturn {
  analytics: PipelineFlowAnalyticsResponse | null
  loading: boolean
  error: string | null
  /** True when analytics data is available (false when no results exist) */
  enabled: boolean
  refetch: () => void
}

export function usePipelineAnalytics(
  pipelineGuid: string | null,
  resultGuid?: string | null,
): UsePipelineAnalyticsReturn {
  const [analytics, setAnalytics] = useState<PipelineFlowAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enabled, setEnabled] = useState(false)

  const fetchAnalytics = useCallback(async () => {
    if (!pipelineGuid) return

    setLoading(true)
    setError(null)
    try {
      const data = await getFlowAnalytics(pipelineGuid, resultGuid ?? undefined)
      setAnalytics(data)
      setEnabled(true)
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 404) {
        // No results — analytics not available
        setEnabled(false)
        setAnalytics(null)
      } else {
        const message = err instanceof Error ? err.message : 'Failed to load flow analytics'
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }, [pipelineGuid, resultGuid])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  return {
    analytics,
    loading,
    error,
    enabled,
    refetch: fetchAnalytics,
  }
}
