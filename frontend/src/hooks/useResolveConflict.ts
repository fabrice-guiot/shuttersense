/**
 * useResolveConflict React hook
 *
 * Mutation hook for batch-resolving conflict groups by updating event attendance.
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 4, US2)
 */

import { useState, useCallback } from 'react'
import * as conflictService from '../services/conflicts'
import type {
  ConflictResolveRequest,
  ConflictResolveResponse,
} from '@/contracts/api/conflict-api'

interface UseResolveConflictReturn {
  resolve: (request: ConflictResolveRequest) => Promise<ConflictResolveResponse>
  loading: boolean
  error: string | null
}

/**
 * Hook for resolving conflict groups by setting event attendance.
 *
 * @param onSuccess - Callback after successful resolution (e.g., refetch conflicts)
 *
 * @example
 * const { resolve, loading } = useResolveConflict({ onSuccess: refetchConflicts })
 * await resolve({ group_id: 'cg_1', decisions: [{ event_guid: 'evt_...', attendance: 'planned' }] })
 */
export const useResolveConflict = (options?: {
  onSuccess?: () => void
}): UseResolveConflictReturn => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const resolve = useCallback(async (request: ConflictResolveRequest) => {
    setLoading(true)
    setError(null)
    try {
      const result = await conflictService.resolveConflict(request)
      options?.onSuccess?.()
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to resolve conflict'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [options?.onSuccess])

  return { resolve, loading, error }
}
