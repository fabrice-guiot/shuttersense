/**
 * Events API service
 *
 * Handles all API calls related to calendar events
 * Issue #39 - Calendar Events feature (Phases 4 & 5)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Event,
  EventDetail,
  EventListParams,
  EventStatsResponse,
  EventCreateRequest,
  EventSeriesCreateRequest,
  EventUpdateRequest,
  UpdateScope,
  PerformerStatus
} from '@/contracts/api/event-api'
import type {
  EventPerformer,
  EventPerformerAddRequest,
  EventPerformerUpdateRequest,
  EventPerformersListResponse
} from '@/contracts/api/performer-api'

/**
 * List events with optional filtering
 *
 * @param params - Query parameters for filtering
 */
export const listEvents = async (params: EventListParams = {}): Promise<Event[]> => {
  const queryParams: Record<string, string | boolean> = {}

  if (params.start_date) queryParams.start_date = params.start_date
  if (params.end_date) queryParams.end_date = params.end_date
  if (params.category_guid) queryParams.category_guid = params.category_guid
  if (params.status) queryParams.status = params.status
  if (params.attendance) queryParams.attendance = params.attendance
  if (params.include_deleted !== undefined) queryParams.include_deleted = params.include_deleted

  const response = await api.get<Event[]>('/events', { params: queryParams })
  return response.data
}

/**
 * Get a single event by GUID
 *
 * @param guid - External ID (evt_xxx format)
 * @param includeDeleted - Include soft-deleted event
 */
export const getEvent = async (guid: string, includeDeleted = false): Promise<EventDetail> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'evt'))
  const params: Record<string, boolean> = {}
  if (includeDeleted) params.include_deleted = true

  const response = await api.get<EventDetail>(`/events/${safeGuid}`, { params })
  return response.data
}

/**
 * Get event statistics (KPIs)
 * Returns aggregated stats for all events
 */
export const getEventStats = async (): Promise<EventStatsResponse> => {
  const response = await api.get<EventStatsResponse>('/events/stats')
  return response.data
}

/**
 * List events for a specific month (convenience function for calendar view)
 *
 * @param year - Full year (e.g., 2026)
 * @param month - Month (1-12)
 */
export const listEventsByMonth = async (year: number, month: number): Promise<Event[]> => {
  // Calculate first and last day of the month
  const startDate = `${year}-${String(month).padStart(2, '0')}-01`

  // Calculate last day of month
  const lastDay = new Date(year, month, 0).getDate()
  const endDate = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`

  return listEvents({ start_date: startDate, end_date: endDate })
}

/**
 * List events for a date range that spans across the visible calendar grid
 * This includes days from adjacent months that appear in the calendar view
 *
 * @param year - Full year (e.g., 2026)
 * @param month - Month (1-12)
 */
export const listEventsForCalendarView = async (year: number, month: number): Promise<Event[]> => {
  // Get the first day of the month
  const firstOfMonth = new Date(year, month - 1, 1)

  // Get the day of week (0 = Sunday)
  const startDayOfWeek = firstOfMonth.getDay()

  // Start from the Sunday before or on the first of the month
  const startDate = new Date(firstOfMonth)
  startDate.setDate(startDate.getDate() - startDayOfWeek)

  // Get the last day of the month
  const lastOfMonth = new Date(year, month, 0)

  // End on the Saturday after or on the last of the month
  const endDayOfWeek = lastOfMonth.getDay()
  const endDate = new Date(lastOfMonth)
  endDate.setDate(endDate.getDate() + (6 - endDayOfWeek))

  const formatDate = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  return listEvents({
    start_date: formatDate(startDate),
    end_date: formatDate(endDate)
  })
}

// =============================================================================
// Create Operations (Phase 5)
// =============================================================================

/**
 * Create a new standalone event
 *
 * @param data - Event creation data
 */
export const createEvent = async (data: EventCreateRequest): Promise<EventDetail> => {
  const response = await api.post<EventDetail>('/events', data)
  return response.data
}

/**
 * Create a new event series
 *
 * @param data - Event series creation data
 */
export const createEventSeries = async (data: EventSeriesCreateRequest): Promise<Event[]> => {
  const response = await api.post<Event[]>('/events/series', data)
  return response.data
}

// =============================================================================
// Update Operations (Phase 5)
// =============================================================================

/**
 * Update an existing event
 *
 * @param guid - Event GUID (evt_xxx format)
 * @param data - Update data (only changed fields)
 */
export const updateEvent = async (guid: string, data: EventUpdateRequest): Promise<EventDetail> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'evt'))
  const response = await api.patch<EventDetail>(`/events/${safeGuid}`, data)
  return response.data
}

// =============================================================================
// Delete Operations (Phase 5)
// =============================================================================

/**
 * Soft delete an event
 *
 * @param guid - Event GUID (evt_xxx format)
 * @param scope - Delete scope for series events (default: single)
 */
export const deleteEvent = async (guid: string, scope: UpdateScope = 'single'): Promise<EventDetail> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'evt'))
  const response = await api.delete<EventDetail>(`/events/${safeGuid}`, {
    params: { scope }
  })
  return response.data
}

/**
 * Restore a soft-deleted event
 *
 * @param guid - Event GUID (evt_xxx format)
 */
export const restoreEvent = async (guid: string): Promise<EventDetail> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'evt'))
  const response = await api.post<EventDetail>(`/events/${safeGuid}/restore`)
  return response.data
}

// =============================================================================
// Event Performer Operations (Phase 11)
// =============================================================================

/**
 * List performers associated with an event
 *
 * @param eventGuid - Event GUID (evt_xxx format)
 */
export const listEventPerformers = async (eventGuid: string): Promise<EventPerformer[]> => {
  const safeGuid = encodeURIComponent(validateGuid(eventGuid, 'evt'))
  const response = await api.get<EventPerformersListResponse>(`/events/${safeGuid}/performers`)
  return response.data.items
}

/**
 * Add a performer to an event
 *
 * @param eventGuid - Event GUID (evt_xxx format)
 * @param performerGuid - Performer GUID (prf_xxx format)
 * @param status - Initial status (default: announced)
 */
export const addPerformerToEvent = async (
  eventGuid: string,
  performerGuid: string,
  status: PerformerStatus = 'announced'
): Promise<EventPerformer> => {
  const safeEventGuid = encodeURIComponent(validateGuid(eventGuid, 'evt'))
  const data: EventPerformerAddRequest = {
    performer_guid: performerGuid,
    status
  }
  const response = await api.post<EventPerformer>(`/events/${safeEventGuid}/performers`, data)
  return response.data
}

/**
 * Update a performer's status on an event
 *
 * @param eventGuid - Event GUID (evt_xxx format)
 * @param performerGuid - Performer GUID (prf_xxx format)
 * @param status - New status
 */
export const updateEventPerformerStatus = async (
  eventGuid: string,
  performerGuid: string,
  status: PerformerStatus
): Promise<EventPerformer> => {
  const safeEventGuid = encodeURIComponent(validateGuid(eventGuid, 'evt'))
  const safePerformerGuid = encodeURIComponent(validateGuid(performerGuid, 'prf'))
  const data: EventPerformerUpdateRequest = { status }
  const response = await api.patch<EventPerformer>(
    `/events/${safeEventGuid}/performers/${safePerformerGuid}`,
    data
  )
  return response.data
}

/**
 * Remove a performer from an event
 *
 * @param eventGuid - Event GUID (evt_xxx format)
 * @param performerGuid - Performer GUID (prf_xxx format)
 */
export const removePerformerFromEvent = async (
  eventGuid: string,
  performerGuid: string
): Promise<void> => {
  const safeEventGuid = encodeURIComponent(validateGuid(eventGuid, 'evt'))
  const safePerformerGuid = encodeURIComponent(validateGuid(performerGuid, 'prf'))
  await api.delete(`/events/${safeEventGuid}/performers/${safePerformerGuid}`)
}
