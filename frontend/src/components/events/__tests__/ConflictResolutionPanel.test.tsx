/**
 * Tests for ConflictResolutionPanel component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 4, US2)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../../tests/mocks/server'
import { ConflictResolutionPanel } from '../ConflictResolutionPanel'
import type { ConflictGroup } from '@/contracts/api/conflict-api'

// ============================================================================
// Fixtures
// ============================================================================

const twoEventGroup: ConflictGroup = {
  group_id: 'cg_1',
  status: 'unresolved',
  events: [
    {
      guid: 'evt_aaa',
      title: 'Morning Workshop',
      event_date: '2026-06-15',
      start_time: '09:00',
      end_time: '12:00',
      is_all_day: false,
      category: null,
      location: { guid: 'loc_1', name: 'NYC Venue', city: 'New York', country: 'US' },
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: {
        venue_quality: 80,
        organizer_reputation: 50,
        performer_lineup: 0,
        logistics_ease: 100,
        readiness: 100,
        composite: 66,
      },
    },
    {
      guid: 'evt_bbb',
      title: 'Afternoon Meetup',
      event_date: '2026-06-15',
      start_time: '11:00',
      end_time: '14:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: {
        venue_quality: 50,
        organizer_reputation: 50,
        performer_lineup: 0,
        logistics_ease: 100,
        readiness: 100,
        composite: 60,
      },
    },
  ],
  edges: [
    {
      event_a_guid: 'evt_aaa',
      event_b_guid: 'evt_bbb',
      conflict_type: 'time_overlap',
      detail: 'Events overlap from 11:00 to 12:00',
    },
  ],
}

const threeEventGroup: ConflictGroup = {
  group_id: 'cg_2',
  status: 'unresolved',
  events: [
    {
      guid: 'evt_x',
      title: 'Event X',
      event_date: '2026-07-01',
      start_time: '10:00',
      end_time: '13:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 50, organizer_reputation: 50, performer_lineup: 50, logistics_ease: 50, readiness: 50, composite: 50 },
    },
    {
      guid: 'evt_y',
      title: 'Event Y',
      event_date: '2026-07-01',
      start_time: '12:00',
      end_time: '15:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 70, organizer_reputation: 80, performer_lineup: 60, logistics_ease: 50, readiness: 50, composite: 62 },
    },
    {
      guid: 'evt_z',
      title: 'Event Z',
      event_date: '2026-07-01',
      start_time: '14:00',
      end_time: '17:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 90, organizer_reputation: 90, performer_lineup: 80, logistics_ease: 80, readiness: 80, composite: 84 },
    },
  ],
  edges: [
    { event_a_guid: 'evt_x', event_b_guid: 'evt_y', conflict_type: 'time_overlap', detail: 'Overlap 12:00-13:00' },
    { event_a_guid: 'evt_y', event_b_guid: 'evt_z', conflict_type: 'time_overlap', detail: 'Overlap 14:00-15:00' },
  ],
}

const resolvedGroup: ConflictGroup = {
  group_id: 'cg_3',
  status: 'resolved',
  events: [
    {
      guid: 'evt_kept',
      title: 'Kept Event',
      event_date: '2026-08-01',
      start_time: '10:00',
      end_time: '15:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 80, organizer_reputation: 80, performer_lineup: 80, logistics_ease: 80, readiness: 80, composite: 80 },
    },
    {
      guid: 'evt_skipped',
      title: 'Skipped Event',
      event_date: '2026-08-01',
      start_time: '12:00',
      end_time: '17:00',
      is_all_day: false,
      category: null,
      location: null,
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'skipped',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 40, organizer_reputation: 40, performer_lineup: 40, logistics_ease: 40, readiness: 40, composite: 40 },
    },
  ],
  edges: [
    { event_a_guid: 'evt_kept', event_b_guid: 'evt_skipped', conflict_type: 'time_overlap', detail: 'Events overlap' },
  ],
}

// ============================================================================
// Tests
// ============================================================================

describe('ConflictResolutionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders empty state when no groups', () => {
    render(<ConflictResolutionPanel groups={[]} />)
    expect(screen.getByText('No conflicts on this day')).toBeInTheDocument()
  })

  test('renders conflict group cards with event names', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    expect(screen.getByText('Morning Workshop')).toBeInTheDocument()
    expect(screen.getByText('Afternoon Meetup')).toBeInTheDocument()
  })

  test('renders composite scores for events', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    expect(screen.getByText('66')).toBeInTheDocument()
    expect(screen.getByText('60')).toBeInTheDocument()
  })

  test('shows conflict type label', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    expect(screen.getByText('Time Overlap')).toBeInTheDocument()
  })

  test('shows Skip button for each unresolved event', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    const skipButtons = screen.getAllByRole('button', { name: /Skip/i })
    expect(skipButtons).toHaveLength(2)
  })

  test('Skip button sends single-event skip payload', async () => {
    let capturedPayload: any = null
    server.use(
      http.post('/api/events/conflicts/resolve', async ({ request }) => {
        capturedPayload = await request.json()
        return HttpResponse.json({ success: true, updated_count: 1 })
      })
    )

    const user = userEvent.setup()
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)

    // Click "Skip" on the first event (Morning Workshop)
    const skipButtons = screen.getAllByRole('button', { name: /Skip/i })
    await user.click(skipButtons[0])

    await waitFor(() => {
      expect(capturedPayload).not.toBeNull()
    })

    // Only the skipped event should be in the payload
    expect(capturedPayload.group_id).toBe('cg_1')
    expect(capturedPayload.decisions).toEqual([
      { event_guid: 'evt_aaa', attendance: 'skipped' },
    ])
  })

  test('3-event group: skipping one event only skips that event', async () => {
    let capturedPayload: any = null
    server.use(
      http.post('/api/events/conflicts/resolve', async ({ request }) => {
        capturedPayload = await request.json()
        return HttpResponse.json({ success: true, updated_count: 1 })
      })
    )

    const user = userEvent.setup()
    render(<ConflictResolutionPanel groups={[threeEventGroup]} />)

    // Click "Skip" on Event Y (middle event)
    const skipButtons = screen.getAllByRole('button', { name: /Skip/i })
    await user.click(skipButtons[1])

    await waitFor(() => {
      expect(capturedPayload).not.toBeNull()
    })

    expect(capturedPayload.group_id).toBe('cg_2')
    // Only Event Y should be skipped — others remain unchanged
    expect(capturedPayload.decisions).toEqual([
      { event_guid: 'evt_y', attendance: 'skipped' },
    ])
  })

  test('resolved groups show Restore button for skipped events', () => {
    render(<ConflictResolutionPanel groups={[resolvedGroup]} />)

    expect(screen.getByText('Kept Event')).toBeInTheDocument()
    expect(screen.getByText('Skipped Event')).toBeInTheDocument()
    expect(screen.getByText('Resolved')).toBeInTheDocument()

    // Skipped event should have Restore button
    expect(screen.getByRole('button', { name: /Restore/i })).toBeInTheDocument()
    // No Skip buttons for resolved groups (non-skipped events don't get Skip)
    expect(screen.queryByRole('button', { name: /Skip/i })).not.toBeInTheDocument()
  })

  test('Restore button sends planned payload for skipped event', async () => {
    let capturedPayload: any = null
    server.use(
      http.post('/api/events/conflicts/resolve', async ({ request }) => {
        capturedPayload = await request.json()
        return HttpResponse.json({ success: true, updated_count: 1 })
      })
    )

    const user = userEvent.setup()
    render(<ConflictResolutionPanel groups={[resolvedGroup]} />)

    const restoreButton = screen.getByRole('button', { name: /Restore/i })
    await user.click(restoreButton)

    await waitFor(() => {
      expect(capturedPayload).not.toBeNull()
    })

    expect(capturedPayload.decisions).toEqual([
      { event_guid: 'evt_skipped', attendance: 'planned' },
    ])
  })

  test('calls onResolved callback after successful skip', async () => {
    server.use(
      http.post('/api/events/conflicts/resolve', () => {
        return HttpResponse.json({ success: true, updated_count: 1 })
      })
    )

    const onResolved = vi.fn()
    const user = userEvent.setup()
    render(<ConflictResolutionPanel groups={[twoEventGroup]} onResolved={onResolved} />)

    const skipButtons = screen.getAllByRole('button', { name: /Skip/i })
    await user.click(skipButtons[0])

    await waitFor(() => {
      expect(onResolved).toHaveBeenCalledTimes(1)
    })
  })

  test('shows event location when available', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    expect(screen.getByText('NYC Venue')).toBeInTheDocument()
  })

  test('shows event time range', () => {
    render(<ConflictResolutionPanel groups={[twoEventGroup]} />)
    expect(screen.getByText('09:00')).toBeInTheDocument()
    expect(screen.getByText('11:00')).toBeInTheDocument()
  })
})
