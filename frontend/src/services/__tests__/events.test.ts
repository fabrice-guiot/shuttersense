import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listEvents,
  getEvent,
  getEventStats,
  getEventDashboardStats,
  listEventsByMonth,
  listEventsForCalendarView,
  createEvent,
  createEventSeries,
  updateEvent,
  deleteEvent,
  restoreEvent,
  listEventPerformers,
  addPerformerToEvent,
  updateEventPerformerStatus,
  removePerformerFromEvent,
} from '@/services/events'
import type {
  Event,
  EventDetail,
  EventListParams,
  EventStatsResponse,
  EventDashboardStatsResponse,
  EventCreateRequest,
  EventSeriesCreateRequest,
  EventUpdateRequest,
} from '@/contracts/api/event-api'
import type {
  EventPerformer,
  EventPerformersListResponse,
} from '@/contracts/api/performer-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Events Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listEvents', () => {
    test('lists events without filters', async () => {
      const mockEvents: Event[] = [
        {
          guid: 'evt_01hgw2bbg00000000000000001',
          title: 'Test Event',
          event_date: '2026-01-15',
          start_time: '10:00:00',
          end_time: '12:00:00',
          is_all_day: false,
          input_timezone: 'America/New_York',
          status: 'confirmed',
          attendance: 'planned',
          category: {
            guid: 'cat_01hgw2bbg00000000000000001',
            name: 'Photography',
            icon: 'Camera',
            color: '#ff0000',
          },
          location: null,
          series_guid: null,
          sequence_number: null,
          series_total: null,
          website: null,
          instagram_handle: null,
          instagram_url: null,
          ticket_required: false,
          ticket_status: null,
          timeoff_required: false,
          timeoff_status: null,
          travel_required: false,
          travel_status: null,
          is_deadline: false,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.mocked(api.get).mockResolvedValue({ data: mockEvents })

      const result = await listEvents()

      expect(api.get).toHaveBeenCalledWith('/events', { params: {} })
      expect(result).toEqual(mockEvents)
    })

    test('lists events with all query parameters', async () => {
      const params: EventListParams = {
        start_date: '2026-01-01',
        end_date: '2026-01-31',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        status: 'confirmed',
        attendance: 'attended',
        include_deleted: true,
        preset: 'upcoming_30d',
      }

      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listEvents(params)

      expect(api.get).toHaveBeenCalledWith('/events', {
        params: {
          start_date: '2026-01-01',
          end_date: '2026-01-31',
          category_guid: 'cat_01hgw2bbg00000000000000001',
          status: 'confirmed',
          attendance: 'attended',
          include_deleted: true,
          preset: 'upcoming_30d',
        },
      })
    })
  })

  describe('getEvent', () => {
    test('fetches a single event by GUID', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      const mockEvent: EventDetail = {
        guid: eventGuid,
        title: 'Test Event',
        event_date: '2026-01-15',
        start_time: '10:00:00',
        end_time: '12:00:00',
        is_all_day: false,
        input_timezone: 'America/New_York',
        status: 'confirmed',
        attendance: 'planned',
        category: {
          guid: 'cat_01hgw2bbg00000000000000001',
          name: 'Photography',
          icon: 'Camera',
          color: '#ff0000',
        },
        location: null,
        organizer: null,
        performers: [],
        series: null,
        series_guid: null,
        sequence_number: null,
        series_total: null,
        description: 'Event description',
        website: null,
        instagram_handle: null,
        instagram_url: null,
        ticket_required: false,
        ticket_status: null,
        ticket_purchase_date: null,
        timeoff_required: false,
        timeoff_status: null,
        timeoff_booking_date: null,
        travel_required: false,
        travel_status: null,
        travel_booking_date: null,
        deadline_date: null,
        deadline_time: null,
        is_deadline: false,
        deleted_at: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockEvent })

      const result = await getEvent(eventGuid)

      expect(api.get).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}`, {
        params: {},
      })
      expect(result).toEqual(mockEvent)
    })

    test('fetches event including deleted', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      vi.mocked(api.get).mockResolvedValue({ data: {} })

      await getEvent(eventGuid, true)

      expect(api.get).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}`, {
        params: { include_deleted: true },
      })
    })

    test('throws error for invalid GUID', async () => {
      await expect(getEvent('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('getEventStats', () => {
    test('fetches event statistics', async () => {
      const mockResponse: EventStatsResponse = {
        total_count: 50,
        upcoming_count: 15,
        this_month_count: 8,
        attended_count: 30,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getEventStats()

      expect(api.get).toHaveBeenCalledWith('/events/stats')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getEventDashboardStats', () => {
    test('fetches event dashboard statistics', async () => {
      const mockResponse: EventDashboardStatsResponse = {
        upcoming_30d_count: 12,
        needs_tickets_count: 3,
        needs_pto_count: 2,
        needs_travel_count: 4,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getEventDashboardStats()

      expect(api.get).toHaveBeenCalledWith('/events/dashboard-stats')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('listEventsByMonth', () => {
    test('lists events for a specific month', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listEventsByMonth(2026, 1)

      expect(api.get).toHaveBeenCalledWith('/events', {
        params: {
          start_date: '2026-01-01',
          end_date: '2026-01-31',
        },
      })
    })

    test('handles February correctly', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listEventsByMonth(2026, 2)

      expect(api.get).toHaveBeenCalledWith('/events', {
        params: {
          start_date: '2026-02-01',
          end_date: '2026-02-28',
        },
      })
    })

    test('handles February in leap year', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listEventsByMonth(2024, 2)

      expect(api.get).toHaveBeenCalledWith('/events', {
        params: {
          start_date: '2024-02-01',
          end_date: '2024-02-29',
        },
      })
    })
  })

  describe('listEventsForCalendarView', () => {
    test('lists events for calendar grid including adjacent months', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listEventsForCalendarView(2026, 1)

      // Should include days from December 2025 and February 2026
      // January 1, 2026 is a Thursday, so starts from Sunday Dec 28, 2025
      expect(api.get).toHaveBeenCalledWith('/events', {
        params: {
          start_date: '2025-12-28',
          end_date: '2026-02-07',
        },
      })
    })
  })

  describe('createEvent', () => {
    test('creates a new standalone event', async () => {
      const requestData: EventCreateRequest = {
        title: 'New Event',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        event_date: '2026-02-15',
        start_time: '14:00',
        end_time: '16:00',
        is_all_day: false,
        status: 'confirmed',
      }

      const mockEvent: EventDetail = {
        guid: 'evt_01hgw2bbg00000000000000001',
        title: requestData.title,
        event_date: requestData.event_date,
        start_time: '14:00:00',
        end_time: '16:00:00',
        is_all_day: false,
        input_timezone: null,
        status: 'confirmed',
        attendance: 'planned',
        category: {
          guid: 'cat_01hgw2bbg00000000000000001',
          name: 'Photography',
          icon: 'Camera',
          color: '#ff0000',
        },
        location: null,
        organizer: null,
        performers: [],
        series: null,
        series_guid: null,
        sequence_number: null,
        series_total: null,
        description: null,
        website: null,
        instagram_handle: null,
        instagram_url: null,
        ticket_required: null,
        ticket_status: null,
        ticket_purchase_date: null,
        timeoff_required: null,
        timeoff_status: null,
        timeoff_booking_date: null,
        travel_required: null,
        travel_status: null,
        travel_booking_date: null,
        deadline_date: null,
        deadline_time: null,
        is_deadline: false,
        deleted_at: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockEvent })

      const result = await createEvent(requestData)

      expect(api.post).toHaveBeenCalledWith('/events', requestData)
      expect(result).toEqual(mockEvent)
    })
  })

  describe('createEventSeries', () => {
    test('creates a new event series', async () => {
      const requestData: EventSeriesCreateRequest = {
        title: 'Monthly Workshop Series',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        event_dates: ['2026-01-15', '2026-02-15', '2026-03-15'],
        start_time: '10:00',
        end_time: '12:00',
        status: 'confirmed',
      }

      const mockEvents: Event[] = [
        {
          guid: 'evt_01hgw2bbg00000000000000001',
          title: requestData.title,
          event_date: '2026-01-15',
          start_time: '10:00:00',
          end_time: '12:00:00',
          is_all_day: false,
          input_timezone: null,
          status: 'confirmed',
          attendance: 'planned',
          category: {
            guid: 'cat_01hgw2bbg00000000000000001',
            name: 'Photography',
            icon: 'Camera',
            color: '#ff0000',
          },
          location: null,
          series_guid: 'ser_01hgw2bbg00000000000000001',
          sequence_number: 1,
          series_total: 3,
          website: null,
          instagram_handle: null,
          instagram_url: null,
          ticket_required: false,
          ticket_status: null,
          timeoff_required: false,
          timeoff_status: null,
          travel_required: false,
          travel_status: null,
          is_deadline: false,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.mocked(api.post).mockResolvedValue({ data: mockEvents })

      const result = await createEventSeries(requestData)

      expect(api.post).toHaveBeenCalledWith('/events/series', requestData)
      expect(result).toEqual(mockEvents)
    })
  })

  describe('updateEvent', () => {
    test('updates an existing event', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'
      const requestData: EventUpdateRequest = {
        title: 'Updated Event Title',
        status: 'completed',
        attendance: 'attended',
      }

      const mockEvent: EventDetail = {
        guid: eventGuid,
        title: requestData.title!,
        event_date: '2026-01-15',
        start_time: '10:00:00',
        end_time: '12:00:00',
        is_all_day: false,
        input_timezone: null,
        status: 'completed',
        attendance: 'attended',
        category: {
          guid: 'cat_01hgw2bbg00000000000000001',
          name: 'Photography',
          icon: 'Camera',
          color: '#ff0000',
        },
        location: null,
        organizer: null,
        performers: [],
        series: null,
        series_guid: null,
        sequence_number: null,
        series_total: null,
        description: null,
        website: null,
        instagram_handle: null,
        instagram_url: null,
        ticket_required: null,
        ticket_status: null,
        ticket_purchase_date: null,
        timeoff_required: null,
        timeoff_status: null,
        timeoff_booking_date: null,
        travel_required: null,
        travel_status: null,
        travel_booking_date: null,
        deadline_date: null,
        deadline_time: null,
        is_deadline: false,
        deleted_at: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockEvent })

      const result = await updateEvent(eventGuid, requestData)

      expect(api.patch).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}`, requestData)
      expect(result).toEqual(mockEvent)
    })
  })

  describe('deleteEvent', () => {
    test('soft deletes an event with default scope', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      const mockEvent: EventDetail = {
        guid: eventGuid,
        title: 'Deleted Event',
        event_date: '2026-01-15',
        start_time: null,
        end_time: null,
        is_all_day: true,
        input_timezone: null,
        status: 'cancelled',
        attendance: 'skipped',
        category: {
          guid: 'cat_01hgw2bbg00000000000000001',
          name: 'Photography',
          icon: 'Camera',
          color: '#ff0000',
        },
        location: null,
        organizer: null,
        performers: [],
        series: null,
        series_guid: null,
        sequence_number: null,
        series_total: null,
        description: null,
        website: null,
        instagram_handle: null,
        instagram_url: null,
        ticket_required: null,
        ticket_status: null,
        ticket_purchase_date: null,
        timeoff_required: null,
        timeoff_status: null,
        timeoff_booking_date: null,
        travel_required: null,
        travel_status: null,
        travel_booking_date: null,
        deadline_date: null,
        deadline_time: null,
        is_deadline: false,
        deleted_at: '2026-01-01T12:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.delete).mockResolvedValue({ data: mockEvent })

      const result = await deleteEvent(eventGuid)

      expect(api.delete).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}`, {
        params: { scope: 'single' },
      })
      expect(result).toEqual(mockEvent)
    })

    test('deletes event series with all scope', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await deleteEvent(eventGuid, 'all')

      expect(api.delete).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}`, {
        params: { scope: 'all' },
      })
    })
  })

  describe('restoreEvent', () => {
    test('restores a soft-deleted event', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      const mockEvent: EventDetail = {
        guid: eventGuid,
        title: 'Restored Event',
        event_date: '2026-01-15',
        start_time: null,
        end_time: null,
        is_all_day: true,
        input_timezone: null,
        status: 'confirmed',
        attendance: 'planned',
        category: {
          guid: 'cat_01hgw2bbg00000000000000001',
          name: 'Photography',
          icon: 'Camera',
          color: '#ff0000',
        },
        location: null,
        organizer: null,
        performers: [],
        series: null,
        series_guid: null,
        sequence_number: null,
        series_total: null,
        description: null,
        website: null,
        instagram_handle: null,
        instagram_url: null,
        ticket_required: null,
        ticket_status: null,
        ticket_purchase_date: null,
        timeoff_required: null,
        timeoff_status: null,
        timeoff_booking_date: null,
        travel_required: null,
        travel_status: null,
        travel_booking_date: null,
        deadline_date: null,
        deadline_time: null,
        is_deadline: false,
        deleted_at: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockEvent })

      const result = await restoreEvent(eventGuid)

      expect(api.post).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}/restore`)
      expect(result).toEqual(mockEvent)
    })
  })

  describe('listEventPerformers', () => {
    test('lists performers for an event', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'

      const mockPerformers: EventPerformer[] = [
        {
          performer: {
            guid: 'prf_01hgw2bbg00000000000000001',
            name: 'Performer Name',
            website: 'https://example.com',
            instagram_handle: '@performer',
            instagram_url: 'https://instagram.com/performer',
            category: {
              guid: 'cat_01hgw2bbg00000000000000001',
              name: 'Photography',
              icon: 'Camera',
              color: '#ff0000',
            },
            additional_info: null,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
          status: 'confirmed',
          added_at: '2026-01-01T00:00:00Z',
        },
      ]

      const mockResponse: EventPerformersListResponse = {
        items: mockPerformers,
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listEventPerformers(eventGuid)

      expect(api.get).toHaveBeenCalledWith(`/events/${encodeURIComponent(eventGuid)}/performers`)
      expect(result).toEqual(mockPerformers)
    })
  })

  describe('addPerformerToEvent', () => {
    test('adds a performer to an event with default status', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'
      const performerGuid = 'prf_01hgw2bbg00000000000000001'

      const mockPerformer: EventPerformer = {
        performer: {
          guid: performerGuid,
          name: 'Performer Name',
          website: null,
          instagram_handle: null,
          instagram_url: null,
          category: {
            guid: 'cat_01hgw2bbg00000000000000001',
            name: 'Photography',
            icon: 'Camera',
            color: '#ff0000',
          },
          additional_info: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        status: 'announced',
        added_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPerformer })

      const result = await addPerformerToEvent(eventGuid, performerGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/events/${encodeURIComponent(eventGuid)}/performers`,
        {
          performer_guid: performerGuid,
          status: 'announced',
        }
      )
      expect(result).toEqual(mockPerformer)
    })

    test('adds a performer with custom status', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'
      const performerGuid = 'prf_01hgw2bbg00000000000000001'

      vi.mocked(api.post).mockResolvedValue({ data: {} })

      await addPerformerToEvent(eventGuid, performerGuid, 'confirmed')

      expect(api.post).toHaveBeenCalledWith(
        `/events/${encodeURIComponent(eventGuid)}/performers`,
        {
          performer_guid: performerGuid,
          status: 'confirmed',
        }
      )
    })
  })

  describe('updateEventPerformerStatus', () => {
    test('updates a performer status', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'
      const performerGuid = 'prf_01hgw2bbg00000000000000001'

      const mockPerformer: EventPerformer = {
        performer: {
          guid: performerGuid,
          name: 'Performer Name',
          website: null,
          instagram_handle: null,
          instagram_url: null,
          category: {
            guid: 'cat_01hgw2bbg00000000000000001',
            name: 'Photography',
            icon: 'Camera',
            color: '#ff0000',
          },
          additional_info: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        status: 'cancelled',
        added_at: '2026-01-01T00:00:00Z',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockPerformer })

      const result = await updateEventPerformerStatus(eventGuid, performerGuid, 'cancelled')

      expect(api.patch).toHaveBeenCalledWith(
        `/events/${encodeURIComponent(eventGuid)}/performers/${encodeURIComponent(performerGuid)}`,
        { status: 'cancelled' }
      )
      expect(result).toEqual(mockPerformer)
    })
  })

  describe('removePerformerFromEvent', () => {
    test('removes a performer from an event', async () => {
      const eventGuid = 'evt_01hgw2bbg00000000000000001'
      const performerGuid = 'prf_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await removePerformerFromEvent(eventGuid, performerGuid)

      expect(api.delete).toHaveBeenCalledWith(
        `/events/${encodeURIComponent(eventGuid)}/performers/${encodeURIComponent(performerGuid)}`
      )
    })
  })
})
