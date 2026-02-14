/**
 * useConflicts React hook
 *
 * Manages conflict detection state for calendar views.
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 3, US1)
 */

import { useState, useCallback } from 'react'
import * as conflictService from '../services/conflicts'
import type {
  ConflictDetectionResponse,
  ConflictType,
  ConflictGroupStatus,
} from '@/contracts/api/conflict-api'

// ============================================================================
// Lookup Types
// ============================================================================

/** Per-day conflict summary for calendar cell indicators */
export interface DayConflictSummary {
  unresolved: number
  resolved: number
}

/** Per-event conflict info for event card badges */
export interface EventConflictInfo {
  groupStatus: ConflictGroupStatus
  conflicts: Array<{
    type: ConflictType
    otherEventTitle: string
    detail: string
  }>
}

// ============================================================================
// Lookup Builder
// ============================================================================

/**
 * Build lookup maps from conflict detection response.
 *
 * @returns byDate - Map of date string to conflict counts per day
 * @returns byEvent - Map of event GUID to conflict info
 */
export function buildConflictLookups(response: ConflictDetectionResponse): {
  byDate: Map<string, DayConflictSummary>
  byEvent: Map<string, EventConflictInfo>
} {
  const byDate = new Map<string, DayConflictSummary>()
  const byEvent = new Map<string, EventConflictInfo>()

  for (const group of response.conflict_groups) {
    // Collect all dates this conflict group spans
    const dates = new Set(group.events.map(e => e.event_date))
    for (const dateStr of dates) {
      const existing = byDate.get(dateStr) || { unresolved: 0, resolved: 0 }
      if (group.status === 'resolved') {
        existing.resolved++
      } else {
        existing.unresolved++
      }
      byDate.set(dateStr, existing)
    }

    // Build per-event conflict info
    for (const event of group.events) {
      const edges = group.edges
        .filter(e => e.event_a_guid === event.guid || e.event_b_guid === event.guid)
        .map(edge => {
          const otherGuid = edge.event_a_guid === event.guid
            ? edge.event_b_guid
            : edge.event_a_guid
          const otherEvent = group.events.find(e => e.guid === otherGuid)
          return {
            type: edge.conflict_type,
            otherEventTitle: otherEvent?.title || 'Unknown',
            detail: edge.detail,
          }
        })

      const existing = byEvent.get(event.guid)
      if (existing) {
        // Event appears in multiple conflict groups — merge
        existing.conflicts.push(...edges)
        // Escalate status: unresolved > partially_resolved > resolved
        if (group.status === 'unresolved') {
          existing.groupStatus = 'unresolved'
        } else if (group.status === 'partially_resolved' && existing.groupStatus === 'resolved') {
          existing.groupStatus = 'partially_resolved'
        }
      } else {
        byEvent.set(event.guid, {
          groupStatus: group.status,
          conflicts: edges,
        })
      }
    }
  }

  return { byDate, byEvent }
}

// ============================================================================
// Hook
// ============================================================================

interface UseConflictsReturn {
  data: ConflictDetectionResponse | null
  loading: boolean
  error: string | null
  detectConflicts: (startDate: string, endDate: string) => Promise<ConflictDetectionResponse>
}

/**
 * Hook for detecting scheduling conflicts within a date range.
 *
 * @example
 * const { data, loading, detectConflicts } = useConflicts()
 * useEffect(() => { detectConflicts('2026-06-01', '2026-06-30') }, [])
 */
export const useConflicts = (): UseConflictsReturn => {
  const [data, setData] = useState<ConflictDetectionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const detect = useCallback(async (startDate: string, endDate: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await conflictService.detectConflicts(startDate, endDate)
      setData(result)
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to detect conflicts'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, detectConflicts: detect }
}
