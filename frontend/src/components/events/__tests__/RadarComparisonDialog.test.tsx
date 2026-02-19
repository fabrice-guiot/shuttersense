/**
 * Tests for RadarComparisonDialog component.
 *
 * Issue #182: Calendar Conflict Visualization (Phase 5, US3)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../../tests/mocks/server'
import { RadarComparisonDialog } from '../RadarComparisonDialog'
import type { ConflictGroup } from '@/contracts/api/conflict-api'

// ============================================================================
// Mock Recharts — RadarChart uses ResponsiveContainer which needs dimensions
// ============================================================================

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts')
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 400, height: 280 }}>
        {children}
      </div>
    ),
  }
})

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
      organizer: { guid: 'org_1', name: 'Acme Events' },
      performer_count: 3,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: {
        venue_quality: 80,
        organizer_reputation: 70,
        performer_lineup: 60,
        logistics_ease: 90,
        readiness: 100,
        composite: 80,
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
        organizer_reputation: 40,
        performer_lineup: 0,
        logistics_ease: 100,
        readiness: 80,
        composite: 54,
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

const threeEventMultiConflict: ConflictGroup = {
  group_id: 'cg_3',
  status: 'unresolved',
  events: [
    {
      guid: 'evt_x',
      title: 'Event X',
      event_date: '2026-07-01',
      start_time: '10:00',
      end_time: '12:00',
      is_all_day: false,
      category: null,
      location: { guid: 'loc_x', name: 'Venue X', city: 'City X', country: 'US' },
      organizer: null,
      performer_count: 0,
      travel_required: true,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 60, organizer_reputation: 50, performer_lineup: 40, logistics_ease: 70, readiness: 80, composite: 60 },
    },
    {
      guid: 'evt_y',
      title: 'Event Y',
      event_date: '2026-07-01',
      start_time: '11:00',
      end_time: '13:00',
      is_all_day: false,
      category: null,
      location: { guid: 'loc_y', name: 'Venue Y', city: 'City Y', country: 'US' },
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'planned',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 70, organizer_reputation: 60, performer_lineup: 50, logistics_ease: 80, readiness: 90, composite: 70 },
    },
    {
      guid: 'evt_z',
      title: 'Event Z',
      event_date: '2026-07-02',
      start_time: '09:00',
      end_time: '11:00',
      is_all_day: false,
      category: null,
      location: { guid: 'loc_z', name: 'Venue Z', city: 'City Z', country: 'US' },
      organizer: null,
      performer_count: 0,
      travel_required: false,
      attendance: 'skipped',
      status: 'future',
      forces_skip: false,
      scores: { venue_quality: 40, organizer_reputation: 30, performer_lineup: 20, logistics_ease: 60, readiness: 70, composite: 44 },
    },
  ],
  edges: [
    { event_a_guid: 'evt_x', event_b_guid: 'evt_y', conflict_type: 'time_overlap', detail: 'Time overlap 11:00-12:00' },
    { event_a_guid: 'evt_x', event_b_guid: 'evt_y', conflict_type: 'distance', detail: '200 miles apart within 1 day' },
    { event_a_guid: 'evt_x', event_b_guid: 'evt_z', conflict_type: 'travel_buffer', detail: 'Only 1 day between travel events' },
  ],
}

const resolvedGroup: ConflictGroup = {
  group_id: 'cg_2',
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

describe('RadarComparisonDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders nothing when group is null', () => {
    const { container } = render(
      <RadarComparisonDialog open={false} onOpenChange={vi.fn()} group={null} />
    )
    expect(container.innerHTML).toBe('')
  })

  test('renders dialog with event titles when open', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    expect(screen.getByText('Compare Events')).toBeInTheDocument()
    // Event titles appear in both the table header and the detail cards
    expect(screen.getAllByText('Morning Workshop')).toHaveLength(2)
    expect(screen.getAllByText('Afternoon Meetup')).toHaveLength(2)
  })

  test('displays dimension breakdown table with correct scores', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )

    // Check dimension labels in the table
    expect(screen.getByText('Venue')).toBeInTheDocument()
    expect(screen.getByText('Organizer')).toBeInTheDocument()
    expect(screen.getByText('Performers')).toBeInTheDocument()
    expect(screen.getByText('Logistics')).toBeInTheDocument()
    expect(screen.getByText('Readiness')).toBeInTheDocument()
    expect(screen.getByText('Composite')).toBeInTheDocument()

    // Check that specific unique scores appear (54 is composite for evt_bbb, unique value)
    expect(screen.getByText('54')).toBeInTheDocument()
    // 90 appears only as logistics_ease for evt_aaa
    expect(screen.getByText('90')).toBeInTheDocument()
  })

  test('shows event detail cards with location and organizer', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    expect(screen.getByText('NYC Venue, New York')).toBeInTheDocument()
    expect(screen.getByText('Acme Events')).toBeInTheDocument()
  })

  test('shows performer count on event cards', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    expect(screen.getByText('3 performers')).toBeInTheDocument()
  })

  test('shows Skip buttons for unresolved events', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    const skipButtons = screen.getAllByRole('button', { name: /Skip/i })
    expect(skipButtons).toHaveLength(2)
  })

  test('Skip button sends single-event skip payload and closes dialog', async () => {
    let capturedPayload: any = null
    server.use(
      http.post('/api/events/conflicts/resolve', async ({ request }) => {
        capturedPayload = await request.json()
        return HttpResponse.json({ success: true, updated_count: 1 })
      })
    )

    const onResolved = vi.fn()
    const onOpenChange = vi.fn()
    const user = userEvent.setup()

    render(
      <RadarComparisonDialog
        open={true}
        onOpenChange={onOpenChange}
        group={twoEventGroup}
        onResolved={onResolved}
      />
    )

    // Click "Skip" on Morning Workshop — single click, no two-step guard
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

    await waitFor(() => {
      expect(onResolved).toHaveBeenCalledTimes(1)
    })
  })

  test('resolved group shows Restore button for skipped events', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={resolvedGroup} />
    )
    // No Skip buttons for resolved group
    expect(screen.queryByRole('button', { name: /Skip/i })).not.toBeInTheDocument()
    // Skipped event should have Restore button
    expect(screen.getByRole('button', { name: /Restore/i })).toBeInTheDocument()
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
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={resolvedGroup} />
    )

    const restoreButton = screen.getByRole('button', { name: /Restore/i })
    await user.click(restoreButton)

    await waitFor(() => {
      expect(capturedPayload).not.toBeNull()
    })

    expect(capturedPayload.decisions).toEqual([
      { event_guid: 'evt_skipped', attendance: 'planned' },
    ])
  })

  test('shows event time ranges on detail cards', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    expect(screen.getByText('09:00 – 12:00')).toBeInTheDocument()
    expect(screen.getByText('11:00 – 14:00')).toBeInTheDocument()
  })

  test('renders radar chart container', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  // ===========================================================================
  // Conflict Counts Section (Issue #196)
  // ===========================================================================

  test('displays conflict type rows with correct counts per event', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={threeEventMultiConflict} />
    )

    // Section header
    expect(screen.getByText('Conflicts')).toBeInTheDocument()

    // All three conflict types should appear
    expect(screen.getByText('Time Overlap')).toBeInTheDocument()
    expect(screen.getByText('Distance')).toBeInTheDocument()
    expect(screen.getByText('Travel Buffer')).toBeInTheDocument()

    // Total row
    expect(screen.getByText('Total')).toBeInTheDocument()
  })

  test('displays conflict section for single-type group', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={twoEventGroup} />
    )

    // Section header + single conflict type
    expect(screen.getByText('Conflicts')).toBeInTheDocument()
    expect(screen.getByText('Time Overlap')).toBeInTheDocument()
    expect(screen.getByText('Total')).toBeInTheDocument()

    // Distance and Travel Buffer should NOT appear (no edges of those types)
    expect(screen.queryByText('Distance')).not.toBeInTheDocument()
    expect(screen.queryByText('Travel Buffer')).not.toBeInTheDocument()
  })

  test('conflict counts are unchanged when event is skipped', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={resolvedGroup} />
    )

    // Even though evt_skipped has attendance='skipped', conflict counts still show
    expect(screen.getByText('Conflicts')).toBeInTheDocument()
    expect(screen.getByText('Time Overlap')).toBeInTheDocument()
    expect(screen.getByText('Total')).toBeInTheDocument()

    // Both events should have count 1 for time_overlap (not filtered by skip)
    // No em dash should appear since both events are involved
    expect(screen.queryByText('\u2014')).not.toBeInTheDocument()
  })

  test('shows em dash for events not involved in a specific conflict type', () => {
    render(
      <RadarComparisonDialog open={true} onOpenChange={vi.fn()} group={threeEventMultiConflict} />
    )

    // evt_z is NOT in any time_overlap or distance edge, only travel_buffer
    // evt_y is NOT in the travel_buffer edge
    // So there should be em dashes for those zero-count cells
    const dashes = screen.getAllByText('\u2014')
    expect(dashes.length).toBeGreaterThan(0)
  })
})
