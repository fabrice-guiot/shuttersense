/**
 * Event API Contracts
 *
 * Defines TypeScript interfaces for all event-related API endpoints.
 * Issue #39 - Calendar Events feature (Phase 4)
 */

// ============================================================================
// Enums
// ============================================================================

// EventStatus is configurable via Settings > Config > Event Statuses
// Default values: 'future' | 'confirmed' | 'completed' | 'cancelled'
export type EventStatus = string
export type AttendanceStatus = 'planned' | 'attended' | 'skipped'
export type TicketStatus = 'not_purchased' | 'purchased' | 'ready'
export type TimeoffStatus = 'planned' | 'booked' | 'approved'
export type TravelStatus = 'planned' | 'booked'
export type UpdateScope = 'single' | 'this_and_future' | 'all'

// ============================================================================
// Summary Types (for embedded responses)
// ============================================================================

export interface CategorySummary {
  guid: string           // Category GUID (cat_xxx)
  name: string
  icon: string | null
  color: string | null
}

export interface EventSeriesSummary {
  guid: string           // Series GUID (ser_xxx)
  title: string
  total_events: number
  deadline_date: string | null      // ISO date (YYYY-MM-DD)
  deadline_time: string | null      // HH:MM:SS or null
  deadline_entry_guid: string | null // Event GUID of deadline entry
}

export interface LocationSummary {
  guid: string           // Location GUID (loc_xxx)
  name: string
  city: string | null
  country: string | null
  timezone: string | null
}

export interface OrganizerSummary {
  guid: string           // Organizer GUID (org_xxx)
  name: string
}

export type PerformerStatus = 'announced' | 'confirmed' | 'cancelled'

export interface PerformerSummary {
  guid: string           // Performer GUID (prf_xxx)
  name: string
  instagram_handle: string | null
  status: PerformerStatus
}

// ============================================================================
// Entity Types
// ============================================================================

/**
 * Event response for list views.
 * Includes core event fields and computed properties.
 */
export interface Event {
  guid: string                        // Event GUID (evt_xxx)
  title: string                       // Effective title (own or from series)

  // Date/time
  event_date: string                  // ISO date (YYYY-MM-DD)
  start_time: string | null           // HH:MM:SS or null
  end_time: string | null             // HH:MM:SS or null
  is_all_day: boolean
  input_timezone: string | null       // IANA timezone

  // Status
  status: EventStatus
  attendance: AttendanceStatus

  // Category (always included for display)
  category: CategorySummary | null

  // Location (included for calendar/list display)
  location: LocationSummary | null

  // Series info (for "x/n" display)
  series_guid: string | null          // Series GUID if part of series
  sequence_number: number | null
  series_total: number | null

  // Logistics summary (for card display indicators)
  ticket_required: boolean | null
  ticket_status: TicketStatus | null
  timeoff_required: boolean | null
  timeoff_status: TimeoffStatus | null
  travel_required: boolean | null
  travel_status: TravelStatus | null

  // Deadline entry flag (true = this event represents a series deadline)
  is_deadline: boolean

  // Timestamps
  created_at: string                  // ISO 8601 timestamp
  updated_at: string                  // ISO 8601 timestamp
}

/**
 * Event detail response with all fields.
 * Extends Event with full details including related entities.
 */
export interface EventDetail extends Event {
  description: string | null

  // Related entities
  location: LocationSummary | null
  organizer: OrganizerSummary | null
  performers: PerformerSummary[]

  // Series details (if part of series)
  series: EventSeriesSummary | null

  // Logistics - Tickets
  ticket_required: boolean | null
  ticket_status: TicketStatus | null
  ticket_purchase_date: string | null // ISO date

  // Logistics - Time Off
  timeoff_required: boolean | null
  timeoff_status: TimeoffStatus | null
  timeoff_booking_date: string | null // ISO date

  // Logistics - Travel
  travel_required: boolean | null
  travel_status: TravelStatus | null
  travel_booking_date: string | null  // ISO date

  // Deadline
  deadline_date: string | null        // ISO date
  deadline_time: string | null        // HH:MM:SS or null

  // Soft delete
  deleted_at: string | null           // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface EventCreateRequest {
  title: string
  category_guid: string
  event_date: string                  // ISO date (YYYY-MM-DD)

  description?: string | null
  location_guid?: string | null
  organizer_guid?: string | null

  start_time?: string | null          // HH:MM format
  end_time?: string | null            // HH:MM format
  is_all_day?: boolean
  input_timezone?: string | null

  status?: EventStatus
  attendance?: AttendanceStatus

  ticket_required?: boolean | null
  timeoff_required?: boolean | null
  travel_required?: boolean | null
  deadline_date?: string | null       // ISO date
  deadline_time?: string | null       // HH:MM format
}

export interface EventSeriesCreateRequest {
  title: string
  category_guid: string
  event_dates: string[]               // List of ISO dates (minimum 2)

  description?: string | null
  location_guid?: string | null
  organizer_guid?: string | null

  start_time?: string | null          // HH:MM format
  end_time?: string | null            // HH:MM format
  is_all_day?: boolean
  input_timezone?: string | null

  ticket_required?: boolean
  timeoff_required?: boolean
  travel_required?: boolean

  // Deadline for deliverables (creates a deadline entry in the calendar)
  deadline_date?: string | null       // ISO date (e.g., client delivery date)
  deadline_time?: string | null       // HH:MM format (e.g., competition cutoff time)

  // Initial status/attendance for all events in series
  status?: EventStatus
  attendance?: AttendanceStatus
}

export interface EventUpdateRequest {
  title?: string | null
  description?: string | null
  category_guid?: string | null
  location_guid?: string | null
  organizer_guid?: string | null

  event_date?: string | null          // ISO date
  start_time?: string | null          // HH:MM format
  end_time?: string | null            // HH:MM format
  is_all_day?: boolean | null
  input_timezone?: string | null

  status?: EventStatus | null
  attendance?: AttendanceStatus | null

  ticket_required?: boolean | null
  ticket_status?: TicketStatus | null
  ticket_purchase_date?: string | null

  timeoff_required?: boolean | null
  timeoff_status?: TimeoffStatus | null
  timeoff_booking_date?: string | null

  travel_required?: boolean | null
  travel_status?: TravelStatus | null
  travel_booking_date?: string | null

  deadline_date?: string | null
  deadline_time?: string | null        // HH:MM format (for series deadline)

  scope?: UpdateScope                  // For series events (default: single)
}

// ============================================================================
// Query Parameters
// ============================================================================

export interface EventListParams {
  start_date?: string                 // ISO date
  end_date?: string                   // ISO date
  category_guid?: string
  status?: EventStatus
  attendance?: AttendanceStatus
  include_deleted?: boolean
}

// ============================================================================
// API Response Types
// ============================================================================

export interface EventStatsResponse {
  /** Total number of events */
  total_count: number

  /** Events in the future */
  upcoming_count: number

  /** Events this month */
  this_month_count: number

  /** Events marked as attended */
  attended_count: number
}

// ============================================================================
// API Error Response
// ============================================================================

export interface EventErrorResponse {
  detail: string
  code?: string
}

// ============================================================================
// API Endpoint Definitions (OpenAPI-style documentation)
// ============================================================================

/**
 * GET /api/events
 *
 * List events with optional filtering
 *
 * Query Parameters:
 *   - start_date: string (optional) - Start of date range (ISO date)
 *   - end_date: string (optional) - End of date range (ISO date)
 *   - category_guid: string (optional) - Filter by category GUID
 *   - status: EventStatus (optional) - Filter by event status
 *   - attendance: AttendanceStatus (optional) - Filter by attendance
 *   - include_deleted: boolean (optional) - Include soft-deleted events
 * Response: 200 Event[]
 * Errors:
 *   - 400: Invalid query parameters
 *   - 500: Internal server error
 */

/**
 * GET /api/events/{guid}
 *
 * Get event details by GUID
 *
 * Path Parameters:
 *   - guid: string (event GUID, evt_xxx format)
 * Query Parameters:
 *   - include_deleted: boolean (optional) - Include soft-deleted event
 * Response: 200 EventDetail
 * Errors:
 *   - 404: Event not found
 *   - 500: Internal server error
 */

/**
 * GET /api/events/stats
 *
 * Get event statistics (KPIs)
 *
 * Response: 200 EventStatsResponse
 * Errors:
 *   - 500: Internal server error
 */

/**
 * POST /api/events
 *
 * Create a new standalone event
 *
 * Request Body: EventCreateRequest
 * Response: 201 EventDetail
 * Errors:
 *   - 400: Validation error
 *   - 404: Category/Location/Organizer not found
 *   - 500: Internal server error
 */

/**
 * POST /api/events/series
 *
 * Create a new event series
 *
 * Request Body: EventSeriesCreateRequest
 * Response: 201 EventDetail[] (created events)
 * Errors:
 *   - 400: Validation error (needs at least 2 dates)
 *   - 404: Category/Location/Organizer not found
 *   - 500: Internal server error
 */

/**
 * PATCH /api/events/{guid}
 *
 * Update existing event
 *
 * Path Parameters:
 *   - guid: string (event GUID, evt_xxx format)
 * Request Body: EventUpdateRequest
 * Response: 200 EventDetail
 * Errors:
 *   - 400: Validation error
 *   - 404: Event not found
 *   - 500: Internal server error
 */

/**
 * DELETE /api/events/{guid}
 *
 * Soft-delete event
 *
 * Path Parameters:
 *   - guid: string (event GUID, evt_xxx format)
 * Query Parameters:
 *   - scope: UpdateScope (optional) - For series events (default: single)
 * Response: 204 No Content
 * Errors:
 *   - 404: Event not found
 *   - 500: Internal server error
 */
