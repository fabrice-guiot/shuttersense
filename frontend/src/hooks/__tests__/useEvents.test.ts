/**
 * Tests for useEvents hooks
 *
 * Issue #39 - Calendar Events feature (Phases 4 & 5)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  useEvents,
  useEvent,
  useEventStats,
  useCalendar,
  useEventMutations,
} from '../useEvents'
import * as eventService from '@/services/events'
import type {
  Event,
  EventDetail,
  EventListParams,
  EventStatsResponse,
  EventCreateRequest,
  EventSeriesCreateRequest,
  EventUpdateRequest,
} from '@/contracts/api/event-api'

// Mock the service
vi.mock('@/services/events')

/** Helper to create an Event with sensible defaults */
function makeEvent(overrides: Partial<Event> & { guid: string; title: string; event_date: string }): Event {
  return {
    guid: overrides.guid,
    title: overrides.title,
    event_date: overrides.event_date,
    start_time: overrides.start_time ?? null,
    end_time: overrides.end_time ?? null,
    is_all_day: overrides.is_all_day ?? false,
    input_timezone: overrides.input_timezone ?? null,
    status: overrides.status ?? 'future',
    attendance: overrides.attendance ?? 'planned',
    category: overrides.category ?? null,
    location: overrides.location ?? null,
    series_guid: overrides.series_guid ?? null,
    sequence_number: overrides.sequence_number ?? null,
    series_total: overrides.series_total ?? null,
    website: overrides.website ?? null,
    instagram_handle: overrides.instagram_handle ?? null,
    instagram_url: overrides.instagram_url ?? null,
    ticket_required: overrides.ticket_required ?? null,
    ticket_status: overrides.ticket_status ?? null,
    timeoff_required: overrides.timeoff_required ?? null,
    timeoff_status: overrides.timeoff_status ?? null,
    travel_required: overrides.travel_required ?? null,
    travel_status: overrides.travel_status ?? null,
    is_deadline: overrides.is_deadline ?? false,
    created_at: overrides.created_at ?? '2026-01-15T10:00:00Z',
    updated_at: overrides.updated_at ?? '2026-01-15T10:00:00Z',
    audit: overrides.audit ?? null,
  }
}

/** Helper to create an EventDetail with sensible defaults */
function makeEventDetail(overrides: Partial<EventDetail> & { guid: string; title: string; event_date: string }): EventDetail {
  const base = makeEvent(overrides)
  return {
    ...base,
    description: overrides.description ?? null,
    organizer: overrides.organizer ?? null,
    performers: overrides.performers ?? [],
    series: overrides.series ?? null,
    ticket_purchase_date: overrides.ticket_purchase_date ?? null,
    timeoff_booking_date: overrides.timeoff_booking_date ?? null,
    travel_booking_date: overrides.travel_booking_date ?? null,
    deadline_date: overrides.deadline_date ?? null,
    deadline_time: overrides.deadline_time ?? null,
    deleted_at: overrides.deleted_at ?? null,
    audit: overrides.audit ?? null,
  }
}

describe('useEvents', () => {
  const mockEvents: Event[] = [
    makeEvent({
      guid: 'evt_01hgw2bbg00000000000000001',
      title: 'Soccer Practice',
      event_date: '2026-06-15',
      start_time: '14:00',
      end_time: '16:00',
      category: { guid: 'cat_sports', name: 'Sports', icon: null, color: null },
      location: { guid: 'loc_field1', name: 'Field 1', city: null, country: null, timezone: null },
      attendance: 'planned',
      created_at: '2026-01-15T10:00:00Z',
    }),
    makeEvent({
      guid: 'evt_01hgw2bbg00000000000000002',
      title: 'Piano Recital',
      event_date: '2026-06-20',
      start_time: '18:00',
      end_time: '20:00',
      category: { guid: 'cat_music', name: 'Music', icon: null, color: null },
      location: { guid: 'loc_hall1', name: 'Hall 1', city: null, country: null, timezone: null },
      attendance: 'skipped',
      created_at: '2026-01-10T08:00:00Z',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventService.listEvents).mockResolvedValue(mockEvents)
    vi.mocked(eventService.listEventsByMonth).mockResolvedValue(mockEvents)
    vi.mocked(eventService.listEventsForCalendarView).mockResolvedValue(mockEvents)
  })

  it('should not fetch on mount by default', async () => {
    const { result } = renderHook(() => useEvents())

    expect(result.current.loading).toBe(false)
    expect(result.current.events).toEqual([])
    expect(eventService.listEvents).not.toHaveBeenCalled()
  })

  it('should fetch on mount when autoFetch is true', async () => {
    const { result } = renderHook(() => useEvents({}, true))

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.events).toHaveLength(2)
    expect(result.current.events[0].title).toBe('Soccer Practice')
    expect(result.current.error).toBe(null)
  })

  it('should fetch events with filters', async () => {
    const { result } = renderHook(() => useEvents())

    const params: EventListParams = {
      category_guid: 'cat_sports',
      attendance: 'planned',
    }

    await act(async () => {
      await result.current.fetchEvents(params)
    })

    expect(eventService.listEvents).toHaveBeenCalledWith(params)
    expect(result.current.events).toHaveLength(2)
  })

  it('should fetch events by month', async () => {
    const { result } = renderHook(() => useEvents())

    await act(async () => {
      await result.current.fetchEventsByMonth(2026, 6)
    })

    expect(eventService.listEventsByMonth).toHaveBeenCalledWith(2026, 6)
    expect(result.current.events).toHaveLength(2)
  })

  it('should fetch events for calendar view', async () => {
    const { result } = renderHook(() => useEvents())

    await act(async () => {
      await result.current.fetchEventsForCalendarView(2026, 6)
    })

    expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 6)
    expect(result.current.events).toHaveLength(2)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load events'
    vi.mocked(eventService.listEvents).mockRejectedValue(error)

    const { result } = renderHook(() => useEvents())

    await act(async () => {
      try {
        await result.current.fetchEvents()
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to load events')
  })
})

describe('useEvent', () => {
  const mockEvent: EventDetail = makeEventDetail({
    guid: 'evt_01hgw2bbg00000000000000001',
    title: 'Soccer Practice',
    event_date: '2026-06-15',
    start_time: '14:00',
    end_time: '16:00',
    category: { guid: 'cat_sports', name: 'Sports', icon: null, color: null },
    location: { guid: 'loc_field1', name: 'Field 1', city: null, country: null, timezone: null },
    organizer: { guid: 'org_club1', name: 'Club 1' },
    attendance: 'planned',
    description: 'Bring cleats',
    created_at: '2026-01-15T10:00:00Z',
    audit: {
      created_by: { guid: 'usr_admin', display_name: 'Admin User', email: 'admin@example.com' },
      created_at: '2026-01-15T10:00:00Z',
      updated_by: { guid: 'usr_admin', display_name: 'Admin User', email: 'admin@example.com' },
      updated_at: '2026-01-15T10:00:00Z',
    },
    performers: [],
  })

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventService.getEvent).mockResolvedValue(mockEvent)
  })

  it('should fetch event on mount when guid is provided', async () => {
    const { result } = renderHook(() => useEvent('evt_01hgw2bbg00000000000000001'))

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.event).toEqual(mockEvent)
    expect(result.current.error).toBe(null)
    expect(eventService.getEvent).toHaveBeenCalledWith('evt_01hgw2bbg00000000000000001', false)
  })

  it('should not fetch on mount when guid is not provided', async () => {
    const { result } = renderHook(() => useEvent())

    expect(result.current.loading).toBe(false)
    expect(result.current.event).toBe(null)
    expect(eventService.getEvent).not.toHaveBeenCalled()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useEvent('evt_01hgw2bbg00000000000000001', false))

    expect(result.current.loading).toBe(false)
    expect(result.current.event).toBe(null)
    expect(eventService.getEvent).not.toHaveBeenCalled()
  })

  it('should fetch event with includeDeleted flag', async () => {
    const { result } = renderHook(() => useEvent())

    await act(async () => {
      await result.current.fetchEvent('evt_01hgw2bbg00000000000000001', true)
    })

    expect(eventService.getEvent).toHaveBeenCalledWith('evt_01hgw2bbg00000000000000001', true)
    expect(result.current.event).toEqual(mockEvent)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Not found')
    ;(error as any).userMessage = 'Event not found'
    vi.mocked(eventService.getEvent).mockRejectedValue(error)

    // Use autoFetch=false to avoid unhandled rejection from useEffect
    // (fetchEvent re-throws after setting error state)
    const { result } = renderHook(() => useEvent('evt_invalid', false))

    await act(async () => {
      try {
        await result.current.fetchEvent('evt_invalid')
      } catch {
        // Expected — fetchEvent re-throws after setting error state
      }
    })

    expect(result.current.error).toBe('Event not found')
    expect(result.current.event).toBe(null)
  })
})

describe('useEventStats', () => {
  const mockStats: EventStatsResponse = {
    total_count: 150,
    upcoming_count: 45,
    this_month_count: 12,
    attended_count: 98,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventService.getEventStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useEventStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useEventStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(eventService.getEventStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useEventStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(eventService.getEventStats).mockResolvedValue({
      ...mockStats,
      upcoming_count: 50,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.upcoming_count).toBe(50)
    })
  })
})

describe('useCalendar', () => {
  const mockEvents: Event[] = [
    makeEvent({
      guid: 'evt_01hgw2bbg00000000000000001',
      title: 'Soccer Practice',
      event_date: '2026-06-15',
      start_time: '14:00',
      end_time: '16:00',
      category: { guid: 'cat_sports', name: 'Sports', icon: null, color: null },
      location: { guid: 'loc_field1', name: 'Field 1', city: null, country: null, timezone: null },
      attendance: 'planned',
      created_at: '2026-01-15T10:00:00Z',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventService.listEventsForCalendarView).mockResolvedValue(mockEvents)
  })

  it('should fetch events for current month on mount', async () => {
    const { result } = renderHook(() => useCalendar())

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const today = new Date()
    expect(result.current.currentYear).toBe(today.getFullYear())
    expect(result.current.currentMonth).toBe(today.getMonth() + 1)
    expect(result.current.events).toHaveLength(1)
  })

  it('should fetch events for initial year and month', async () => {
    const { result } = renderHook(() => useCalendar(2026, 6))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.currentYear).toBe(2026)
    expect(result.current.currentMonth).toBe(6)
    expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 6)
  })

  it('should navigate to specific month', async () => {
    const { result } = renderHook(() => useCalendar())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToMonth(2026, 12)
    })

    expect(result.current.currentYear).toBe(2026)
    expect(result.current.currentMonth).toBe(12)

    await waitFor(() => {
      expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 12)
    })
  })

  it('should navigate to previous month', async () => {
    const { result } = renderHook(() => useCalendar(2026, 6))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToPreviousMonth()
    })

    expect(result.current.currentYear).toBe(2026)
    expect(result.current.currentMonth).toBe(5)

    await waitFor(() => {
      expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 5)
    })
  })

  it('should wrap to previous year when navigating from January', async () => {
    const { result } = renderHook(() => useCalendar(2026, 1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToPreviousMonth()
    })

    expect(result.current.currentYear).toBe(2025)
    expect(result.current.currentMonth).toBe(12)
  })

  it('should navigate to next month', async () => {
    const { result } = renderHook(() => useCalendar(2026, 6))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToNextMonth()
    })

    expect(result.current.currentYear).toBe(2026)
    expect(result.current.currentMonth).toBe(7)

    await waitFor(() => {
      expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 7)
    })
  })

  it('should wrap to next year when navigating from December', async () => {
    const { result } = renderHook(() => useCalendar(2026, 12))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToNextMonth()
    })

    expect(result.current.currentYear).toBe(2027)
    expect(result.current.currentMonth).toBe(1)
  })

  it('should navigate to today', async () => {
    const { result } = renderHook(() => useCalendar(2026, 12))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.goToToday()
    })

    const today = new Date()
    expect(result.current.currentYear).toBe(today.getFullYear())
    expect(result.current.currentMonth).toBe(today.getMonth() + 1)
  })

  it('should refetch current month events', async () => {
    const { result } = renderHook(() => useCalendar(2026, 6))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.clearAllMocks()

    await act(async () => {
      await result.current.refetch()
    })

    expect(eventService.listEventsForCalendarView).toHaveBeenCalledWith(2026, 6)
  })
})

describe('useEventMutations', () => {
  const mockEventDetail: EventDetail = makeEventDetail({
    guid: 'evt_new',
    title: 'New Event',
    event_date: '2026-06-25',
    start_time: '10:00',
    end_time: '11:00',
    category: { guid: 'cat_sports', name: 'Sports', icon: null, color: null },
    location: { guid: 'loc_field1', name: 'Field 1', city: null, country: null, timezone: null },
    attendance: 'planned',
    created_at: '2026-01-18T12:00:00Z',
    audit: {
      created_by: { guid: 'usr_admin', display_name: 'Admin User', email: 'admin@example.com' },
      created_at: '2026-01-18T12:00:00Z',
      updated_by: { guid: 'usr_admin', display_name: 'Admin User', email: 'admin@example.com' },
      updated_at: '2026-01-18T12:00:00Z',
    },
    performers: [],
  })

  const mockEvents: Event[] = [
    makeEvent({
      guid: 'evt_new_1',
      title: 'Series Event 1',
      event_date: '2026-06-01',
      start_time: '10:00',
      end_time: '11:00',
      category: { guid: 'cat_sports', name: 'Sports', icon: null, color: null },
      location: { guid: 'loc_field1', name: 'Field 1', city: null, country: null, timezone: null },
      attendance: 'planned',
      created_at: '2026-01-18T12:00:00Z',
    }),
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventService.createEvent).mockResolvedValue(mockEventDetail)
    vi.mocked(eventService.createEventSeries).mockResolvedValue(mockEvents)
    vi.mocked(eventService.updateEvent).mockResolvedValue(mockEventDetail)
    vi.mocked(eventService.deleteEvent).mockResolvedValue(mockEventDetail)
    vi.mocked(eventService.restoreEvent).mockResolvedValue(mockEventDetail)
  })

  it('should create a new event', async () => {
    const { result } = renderHook(() => useEventMutations())

    const createRequest: EventCreateRequest = {
      title: 'New Event',
      event_date: '2026-06-25',
      category_guid: 'cat_sports',
      start_time: '10:00',
      end_time: '11:00',
      location_guid: 'loc_field1',
      attendance: 'planned',
    }

    let createdEvent: EventDetail | undefined

    await act(async () => {
      createdEvent = await result.current.createEvent(createRequest)
    })

    expect(createdEvent).toEqual(mockEventDetail)
    expect(eventService.createEvent).toHaveBeenCalledWith(createRequest)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should create an event series', async () => {
    const { result } = renderHook(() => useEventMutations())

    const createRequest: EventSeriesCreateRequest = {
      title: 'Weekly Practice',
      category_guid: 'cat_sports',
      event_dates: ['2026-06-01', '2026-06-08', '2026-06-15', '2026-06-22', '2026-06-29'],
      start_time: '10:00',
      end_time: '11:00',
      location_guid: 'loc_field1',
      attendance: 'planned',
    }

    let createdEvents: Event[] | undefined

    await act(async () => {
      createdEvents = await result.current.createEventSeries(createRequest)
    })

    expect(createdEvents).toEqual(mockEvents)
    expect(eventService.createEventSeries).toHaveBeenCalledWith(createRequest)
  })

  it('should update an event', async () => {
    const { result } = renderHook(() => useEventMutations())

    const updateRequest: EventUpdateRequest = {
      title: 'Updated Event',
      attendance: 'skipped',
      scope: 'single',
    }

    let updatedEvent: EventDetail | undefined

    await act(async () => {
      updatedEvent = await result.current.updateEvent('evt_new', updateRequest)
    })

    expect(updatedEvent).toEqual(mockEventDetail)
    expect(eventService.updateEvent).toHaveBeenCalledWith('evt_new', updateRequest)
  })

  it('should delete an event', async () => {
    const { result } = renderHook(() => useEventMutations())

    await act(async () => {
      await result.current.deleteEvent('evt_new', 'single')
    })

    expect(eventService.deleteEvent).toHaveBeenCalledWith('evt_new', 'single')
  })

  it('should restore an event', async () => {
    const { result } = renderHook(() => useEventMutations())

    let restoredEvent: EventDetail | undefined

    await act(async () => {
      restoredEvent = await result.current.restoreEvent('evt_new')
    })

    expect(restoredEvent).toEqual(mockEventDetail)
    expect(eventService.restoreEvent).toHaveBeenCalledWith('evt_new')
  })

  it('should handle create error', async () => {
    const error = new Error('Validation error')
    ;(error as any).userMessage = 'Invalid event data'
    vi.mocked(eventService.createEvent).mockRejectedValue(error)

    const { result } = renderHook(() => useEventMutations())

    await act(async () => {
      try {
        await result.current.createEvent({} as EventCreateRequest)
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Invalid event data')
  })
})
