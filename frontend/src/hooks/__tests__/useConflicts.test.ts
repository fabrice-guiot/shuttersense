/**
 * Tests for useConflicts hook
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 3, US1)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useConflicts, buildConflictLookups } from '../useConflicts'
import * as conflictService from '@/services/conflicts'
import type {
  ConflictDetectionResponse,
  ConflictGroup,
  ConflictEdge,
  ScoredEvent,
  EventScores,
} from '@/contracts/api/conflict-api'

// Mock the service
vi.mock('@/services/conflicts')

/** Helper to create a ScoredEvent with sensible defaults */
function makeScoredEvent(overrides: Partial<ScoredEvent> & { guid: string; title: string; event_date: string }): ScoredEvent {
  const defaultScores: EventScores = {
    venue_quality: 50,
    organizer_reputation: 50,
    performer_lineup: 0,
    logistics_ease: 50,
    readiness: 50,
    composite: 50,
  }
  return {
    guid: overrides.guid,
    title: overrides.title,
    event_date: overrides.event_date,
    start_time: overrides.start_time ?? null,
    end_time: overrides.end_time ?? null,
    is_all_day: overrides.is_all_day ?? false,
    category: overrides.category ?? null,
    location: overrides.location ?? null,
    organizer: overrides.organizer ?? null,
    performer_count: overrides.performer_count ?? 0,
    travel_required: overrides.travel_required ?? null,
    attendance: overrides.attendance ?? 'planned',
    scores: overrides.scores ?? defaultScores,
  }
}

describe('buildConflictLookups', () => {
  it('should build empty lookups for no conflicts', () => {
    const response: ConflictDetectionResponse = {
      conflict_groups: [],
      scored_events: [],
      summary: {
        total_groups: 0,
        unresolved: 0,
        resolved: 0,
        partially_resolved: 0,
      },
    }

    const { byDate, byEvent } = buildConflictLookups(response)

    expect(byDate.size).toBe(0)
    expect(byEvent.size).toBe(0)
  })

  it('should count edges per date, not groups', () => {
    const events: ScoredEvent[] = [
      makeScoredEvent({
        guid: 'evt_001',
        title: 'Event A',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
      makeScoredEvent({
        guid: 'evt_002',
        title: 'Event B',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
      makeScoredEvent({
        guid: 'evt_003',
        title: 'Event C',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
    ]

    const edges: ConflictEdge[] = [
      {
        event_a_guid: 'evt_001',
        event_b_guid: 'evt_002',
        conflict_type: 'time_overlap',
        detail: '10:00-11:00 vs 10:30-11:30',
      },
      {
        event_a_guid: 'evt_002',
        event_b_guid: 'evt_003',
        conflict_type: 'time_overlap',
        detail: '10:30-11:30 vs 11:00-12:00',
      },
    ]

    const group: ConflictGroup = {
      group_id: 'cg_1',
      events,
      edges,
      status: 'unresolved',
    }

    const response: ConflictDetectionResponse = {
      conflict_groups: [group],
      scored_events: events,
      summary: {
        total_groups: 1,
        unresolved: 1,
        resolved: 0,
        partially_resolved: 0,
      },
    }

    const { byDate } = buildConflictLookups(response)

    expect(byDate.get('2026-06-01')).toEqual({ unresolved: 2, resolved: 0 })
  })

  it('should mark edges as resolved if either event is skipped', () => {
    const events: ScoredEvent[] = [
      makeScoredEvent({
        guid: 'evt_001',
        title: 'Event A',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
      makeScoredEvent({
        guid: 'evt_002',
        title: 'Event B',
        event_date: '2026-06-01',
        attendance: 'skipped',
      }),
    ]

    const edges: ConflictEdge[] = [
      {
        event_a_guid: 'evt_001',
        event_b_guid: 'evt_002',
        conflict_type: 'time_overlap',
        detail: '10:00-11:00 vs 10:30-11:30',
      },
    ]

    const group: ConflictGroup = {
      group_id: 'cg_1',
      events,
      edges,
      status: 'resolved',
    }

    const response: ConflictDetectionResponse = {
      conflict_groups: [group],
      scored_events: events,
      summary: {
        total_groups: 1,
        unresolved: 0,
        resolved: 1,
        partially_resolved: 0,
      },
    }

    const { byDate } = buildConflictLookups(response)

    expect(byDate.get('2026-06-01')).toEqual({ unresolved: 0, resolved: 1 })
  })

  it('should build per-event conflict info with edges', () => {
    const events: ScoredEvent[] = [
      makeScoredEvent({
        guid: 'evt_001',
        title: 'Event A',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
      makeScoredEvent({
        guid: 'evt_002',
        title: 'Event B',
        event_date: '2026-06-01',
        attendance: 'planned',
      }),
    ]

    const edges: ConflictEdge[] = [
      {
        event_a_guid: 'evt_001',
        event_b_guid: 'evt_002',
        conflict_type: 'time_overlap',
        detail: '10:00-11:00 vs 10:30-11:30',
      },
    ]

    const group: ConflictGroup = {
      group_id: 'cg_1',
      events,
      edges,
      status: 'unresolved',
    }

    const response: ConflictDetectionResponse = {
      conflict_groups: [group],
      scored_events: events,
      summary: {
        total_groups: 1,
        unresolved: 1,
        resolved: 0,
        partially_resolved: 0,
      },
    }

    const { byEvent } = buildConflictLookups(response)

    expect(byEvent.get('evt_001')).toEqual({
      groupStatus: 'unresolved',
      conflicts: [
        {
          type: 'time_overlap',
          otherEventTitle: 'Event B',
          detail: '10:00-11:00 vs 10:30-11:30',
        },
      ],
    })

    expect(byEvent.get('evt_002')).toEqual({
      groupStatus: 'unresolved',
      conflicts: [
        {
          type: 'time_overlap',
          otherEventTitle: 'Event A',
          detail: '10:00-11:00 vs 10:30-11:30',
        },
      ],
    })
  })

  it('should merge conflicts when event appears in multiple groups', () => {
    const group1: ConflictGroup = {
      group_id: 'cg_1',
      events: [
        makeScoredEvent({
          guid: 'evt_001',
          title: 'Event A',
          event_date: '2026-06-01',
          attendance: 'planned',
        }),
        makeScoredEvent({
          guid: 'evt_002',
          title: 'Event B',
          event_date: '2026-06-01',
          attendance: 'planned',
        }),
      ],
      edges: [
        {
          event_a_guid: 'evt_001',
          event_b_guid: 'evt_002',
          conflict_type: 'time_overlap',
          detail: 'Conflict 1',
        },
      ],
      status: 'resolved',
    }

    const group2: ConflictGroup = {
      group_id: 'cg_2',
      events: [
        makeScoredEvent({
          guid: 'evt_001',
          title: 'Event A',
          event_date: '2026-06-01',
          attendance: 'planned',
        }),
        makeScoredEvent({
          guid: 'evt_003',
          title: 'Event C',
          event_date: '2026-06-01',
          attendance: 'planned',
        }),
      ],
      edges: [
        {
          event_a_guid: 'evt_001',
          event_b_guid: 'evt_003',
          conflict_type: 'distance',
          detail: 'Conflict 2',
        },
      ],
      status: 'unresolved',
    }

    const response: ConflictDetectionResponse = {
      conflict_groups: [group1, group2],
      scored_events: [],
      summary: {
        total_groups: 2,
        unresolved: 1,
        resolved: 1,
        partially_resolved: 0,
      },
    }

    const { byEvent } = buildConflictLookups(response)

    const evt001Info = byEvent.get('evt_001')
    expect(evt001Info?.groupStatus).toBe('unresolved') // Escalated from resolved
    expect(evt001Info?.conflicts).toHaveLength(2)
  })
})

describe('useConflicts', () => {
  const mockResponse: ConflictDetectionResponse = {
    conflict_groups: [
      {
        group_id: 'cg_1',
        events: [
          makeScoredEvent({
            guid: 'evt_001',
            title: 'Event A',
            event_date: '2026-06-01',
            attendance: 'planned',
          }),
          makeScoredEvent({
            guid: 'evt_002',
            title: 'Event B',
            event_date: '2026-06-01',
            attendance: 'planned',
          }),
        ],
        edges: [
          {
            event_a_guid: 'evt_001',
            event_b_guid: 'evt_002',
            conflict_type: 'time_overlap',
            detail: '10:00-11:00 vs 10:30-11:30',
          },
        ],
        status: 'unresolved',
      },
    ],
    scored_events: [],
    summary: {
      total_groups: 1,
      unresolved: 1,
      resolved: 0,
      partially_resolved: 0,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(conflictService.detectConflicts).mockResolvedValue(mockResponse)
  })

  it('should detect conflicts for a date range', async () => {
    const { result } = renderHook(() => useConflicts())

    expect(result.current.data).toBe(null)
    expect(result.current.loading).toBe(false)

    let detectedData: ConflictDetectionResponse | undefined

    await act(async () => {
      detectedData = await result.current.detectConflicts('2026-06-01', '2026-06-30')
    })

    expect(detectedData).toEqual(mockResponse)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.data).toEqual(mockResponse)
      expect(result.current.error).toBe(null)
    })

    expect(conflictService.detectConflicts).toHaveBeenCalledWith('2026-06-01', '2026-06-30')
  })

  it('should handle detect error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to detect conflicts'
    vi.mocked(conflictService.detectConflicts).mockRejectedValue(error)

    const { result } = renderHook(() => useConflicts())

    await act(async () => {
      try {
        await result.current.detectConflicts('2026-06-01', '2026-06-30')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe('Failed to detect conflicts')
      expect(result.current.data).toBe(null)
    })
  })

  it('should use default error message if userMessage is missing', async () => {
    const error = new Error('Network error')
    vi.mocked(conflictService.detectConflicts).mockRejectedValue(error)

    const { result } = renderHook(() => useConflicts())

    await act(async () => {
      try {
        await result.current.detectConflicts('2026-06-01', '2026-06-30')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    await waitFor(() => {
      expect(result.current.error).toBe('Failed to detect conflicts')
    })
  })
})
