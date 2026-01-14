/**
 * Events Page
 *
 * Display and manage calendar events.
 * Calendar view with event management capabilities.
 *
 * Issue #39 - Calendar Events feature (Phases 4 & 5).
 */

import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, MapPin, Building2, Ticket, Briefcase, Car, Calendar, AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { useCalendar, useEventStats, useEventMutations } from '@/hooks/useEvents'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { EventCalendar, EventList, EventForm, EventPerformersSection } from '@/components/events'
import { useCategories } from '@/hooks/useCategories'
import type { Event, EventDetail, EventCreateRequest, EventUpdateRequest, EventSeriesCreateRequest } from '@/contracts/api/event-api'

export default function EventsPage() {
  // Calendar state and navigation
  const calendar = useCalendar()
  const {
    events,
    loading,
    error,
    currentYear,
    currentMonth,
    goToPreviousMonth,
    goToNextMonth,
    goToToday,
    refetch
  } = calendar

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useEventStats()
  const { setStats } = useHeaderStats()

  // Categories for event form
  const { categories } = useCategories(true)

  // Event mutations
  const mutations = useEventMutations()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Events', value: stats.total_count.toLocaleString() },
        { label: 'Upcoming', value: stats.upcoming_count.toLocaleString() },
        { label: 'This Month', value: stats.this_month_count.toLocaleString() },
        { label: 'Attended', value: stats.attended_count.toLocaleString() }
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  // ============================================================================
  // Dialog States
  // ============================================================================

  // Day detail dialog
  const [selectedDay, setSelectedDay] = useState<{
    date: Date
    events: Event[]
  } | null>(null)

  // Event detail dialog (uses EventDetail for full info including description)
  const [selectedEvent, setSelectedEvent] = useState<EventDetail | null>(null)

  // Create event dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [createDefaultDate, setCreateDefaultDate] = useState<string | undefined>()

  // Edit event dialog
  const [editEvent, setEditEvent] = useState<EventDetail | null>(null)

  // Delete confirmation dialog
  const [deleteEvent, setDeleteEvent] = useState<Event | null>(null)

  // ============================================================================
  // Event Handlers
  // ============================================================================

  // Handle day click - show day detail dialog
  const handleDayClick = (date: Date) => {
    const dateString = formatDateString(date)
    const dayEvents = events.filter(e => e.event_date === dateString)

    if (dayEvents.length > 0) {
      setSelectedDay({ date, events: dayEvents })
    } else {
      // Open create dialog with this date pre-selected
      setCreateDefaultDate(dateString)
      setCreateDialogOpen(true)
    }
  }

  // Fetch event details helper
  const fetchEventDetails = async (eventGuid: string): Promise<EventDetail | null> => {
    try {
      const response = await fetch(`/api/events/${eventGuid}`)
      return await response.json()
    } catch {
      return null
    }
  }

  // Handle event click - show event detail (fetch full details)
  const handleEventClick = async (event: Event) => {
    setSelectedDay(null) // Close day dialog if open
    const fullEvent = await fetchEventDetails(event.guid)
    if (fullEvent) {
      setSelectedEvent(fullEvent)
    } else {
      // If fetch fails, use basic event data (description won't be available)
      setSelectedEvent(event as unknown as EventDetail)
    }
  }

  // Refetch currently selected event (used after performer changes)
  const refetchSelectedEvent = async () => {
    if (selectedEvent) {
      const refreshed = await fetchEventDetails(selectedEvent.guid)
      if (refreshed) {
        setSelectedEvent(refreshed)
      }
    }
  }

  // Handle create button click
  const handleCreateClick = () => {
    setCreateDefaultDate(undefined)
    setCreateDialogOpen(true)
  }

  // Handle create submit
  const handleCreateSubmit = async (data: EventCreateRequest | EventUpdateRequest) => {
    await mutations.createEvent(data as EventCreateRequest)
    setCreateDialogOpen(false)
    await refetch()
    await refetchStats()
  }

  // Handle series create submit
  const handleCreateSeriesSubmit = async (data: EventSeriesCreateRequest) => {
    await mutations.createEventSeries(data)
    setCreateDialogOpen(false)
    await refetch()
    await refetchStats()
  }

  // Handle edit click from detail dialog
  const handleEditClick = async () => {
    if (selectedEvent) {
      // Fetch full event details for editing
      try {
        const response = await fetch(`/api/events/${selectedEvent.guid}`)
        const fullEvent = await response.json()
        setEditEvent(fullEvent)
        setSelectedEvent(null)
      } catch {
        // If fetch fails, use what we have
        setEditEvent(selectedEvent as unknown as EventDetail)
        setSelectedEvent(null)
      }
    }
  }

  // Handle edit submit
  const handleEditSubmit = async (data: EventCreateRequest | EventUpdateRequest) => {
    if (editEvent) {
      await mutations.updateEvent(editEvent.guid, data as EventUpdateRequest)
      setEditEvent(null)
      await refetch()
      await refetchStats()
    }
  }

  // Handle delete click from detail dialog
  const handleDeleteClick = () => {
    if (selectedEvent) {
      setDeleteEvent(selectedEvent)
      setSelectedEvent(null)
    }
  }

  // Handle delete confirm
  const handleDeleteConfirm = async () => {
    if (deleteEvent) {
      await mutations.deleteEvent(deleteEvent.guid, 'single')
      setDeleteEvent(null)
      await refetch()
      await refetchStats()
    }
  }

  // ============================================================================
  // Helpers
  // ============================================================================

  // Helper to format date as YYYY-MM-DD
  const formatDateString = (d: Date): string => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  // Parse ISO date string (YYYY-MM-DD) as local date (not UTC)
  // This prevents the date from shifting when displayed in timezones west of UTC
  const parseLocalDate = (dateStr: string): Date => {
    const [year, month, day] = dateStr.split('-').map(Number)
    return new Date(year, month - 1, day)
  }

  // Format date for display
  const formatDisplayDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Format ISO date string for display (handles timezone correctly)
  const formatDateStr = (dateStr: string, options?: Intl.DateTimeFormatOptions): string => {
    const date = parseLocalDate(dateStr)
    return date.toLocaleDateString('en-US', options || {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Format time in 12-hour format with AM/PM (input: "HH:MM" or "HH:MM:SS")
  const formatTime12h = (timeStr: string): string => {
    const [hoursStr, minutesStr] = timeStr.split(':')
    const hours = parseInt(hoursStr, 10)
    const minutes = minutesStr
    const period = hours >= 12 ? 'PM' : 'AM'
    const hours12 = hours % 12 || 12
    return `${hours12}:${minutes}${period}`
  }

  // Get timezone abbreviation from IANA timezone (e.g., "America/New_York" -> "EST")
  const getTimezoneAbbreviation = (ianaTimezone: string, date?: Date): string => {
    try {
      const dateToUse = date || new Date()
      // Use Intl.DateTimeFormat to get the timezone abbreviation
      const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: ianaTimezone,
        timeZoneName: 'short'
      })
      const parts = formatter.formatToParts(dateToUse)
      const tzPart = parts.find(part => part.type === 'timeZoneName')
      return tzPart?.value || ianaTimezone
    } catch {
      // Fallback to IANA name if formatting fails
      return ianaTimezone
    }
  }

  // Format time with optional timezone display
  const formatTimeWithTimezone = (
    timeStr: string,
    timezone: string | null | undefined,
    eventDate?: string
  ): string => {
    const time12h = formatTime12h(timeStr)
    if (!timezone) {
      return time12h
    }
    const date = eventDate ? new Date(eventDate + 'T00:00:00') : new Date()
    const tzAbbrev = getTimezoneAbbreviation(timezone, date)
    return `${time12h} ${tzAbbrev}`
  }

  return (
    <div className="flex flex-col h-full p-6">
      {/* Action Row (Issue #67 - Single Title Pattern) */}
      <div className="flex justify-end mb-4">
        <Button onClick={handleCreateClick}>
          <Plus className="h-4 w-4 mr-2" />
          New Event
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Calendar View */}
      <div className="flex-1 min-h-0">
        <EventCalendar
          events={events}
          year={currentYear}
          month={currentMonth}
          loading={loading}
          onPreviousMonth={goToPreviousMonth}
          onNextMonth={goToNextMonth}
          onToday={goToToday}
          onEventClick={handleEventClick}
          onDayClick={handleDayClick}
          className="h-full"
        />
      </div>

      {/* Day Detail Dialog */}
      <Dialog
        open={selectedDay !== null}
        onOpenChange={(open) => !open && setSelectedDay(null)}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedDay && formatDisplayDate(selectedDay.date)}
            </DialogTitle>
            <DialogDescription>
              {selectedDay?.events.length} event{selectedDay?.events.length !== 1 ? 's' : ''} on this day
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto">
            {selectedDay && (
              <EventList
                events={selectedDay.events}
                onEventClick={handleEventClick}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Event Detail Dialog */}
      <Dialog
        open={selectedEvent !== null}
        onOpenChange={(open) => !open && setSelectedEvent(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedEvent?.title}</DialogTitle>
            <DialogDescription>
              {selectedEvent && (
                <>
                  {formatDateStr(selectedEvent.event_date)}
                  {selectedEvent.start_time && ` at ${formatTimeWithTimezone(
                    selectedEvent.start_time,
                    selectedEvent.input_timezone,
                    selectedEvent.event_date
                  )}`}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedEvent && (
            <div className="space-y-4 pt-4">
              {/* Description */}
              {selectedEvent.description && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Description</div>
                  <div className="text-sm whitespace-pre-wrap">{selectedEvent.description}</div>
                </div>
              )}

              {/* Category */}
              {selectedEvent.category && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Category</div>
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: selectedEvent.category.color || '#888' }}
                    />
                    <span>{selectedEvent.category.name}</span>
                  </div>
                </div>
              )}

              {/* Location */}
              {selectedEvent.location && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Location</div>
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {selectedEvent.location.name}
                      {selectedEvent.location.city && `, ${selectedEvent.location.city}`}
                      {selectedEvent.location.country && `, ${selectedEvent.location.country}`}
                    </span>
                  </div>
                </div>
              )}

              {/* Time (hidden for deadline events - already shown in header) */}
              {!selectedEvent.is_deadline && !selectedEvent.is_all_day && selectedEvent.start_time && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Time</div>
                  <div>
                    {formatTimeWithTimezone(
                      selectedEvent.start_time,
                      selectedEvent.input_timezone,
                      selectedEvent.event_date
                    )}
                    {selectedEvent.end_time && ` - ${formatTime12h(selectedEvent.end_time)}`}
                  </div>
                </div>
              )}

              {/* Status and Attendance (hidden for deadline events) */}
              {!selectedEvent.is_deadline && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-1">Status</div>
                    <div className="capitalize">{selectedEvent.status}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-1">Attendance</div>
                    <div className="capitalize">{selectedEvent.attendance}</div>
                  </div>
                </div>
              )}

              {/* Deadline (shown separately from Logistics, hidden for deadline events themselves) */}
              {!selectedEvent.is_deadline && selectedEvent.deadline_date && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Deadline</div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>
                      {formatDateStr(selectedEvent.deadline_date, {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                      {selectedEvent.deadline_time && ` at ${formatTime12h(selectedEvent.deadline_time)}`}
                    </span>
                  </div>
                </div>
              )}

              {/* Series Info (hidden for deadline events) */}
              {!selectedEvent.is_deadline && selectedEvent.series_guid && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Series</div>
                  <div>
                    Event {selectedEvent.sequence_number} of {selectedEvent.series_total}
                  </div>
                </div>
              )}

              {/* Organizer */}
              {selectedEvent.organizer && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">Organizer</div>
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span>{selectedEvent.organizer.name}</span>
                  </div>
                </div>
              )}

              {/* Performers Section (hidden for deadline events) */}
              {!selectedEvent.is_deadline && (
                <div className="pt-2 border-t">
                  <EventPerformersSection
                    eventGuid={selectedEvent.guid}
                    categoryGuid={selectedEvent.category?.guid || null}
                    performers={selectedEvent.performers || []}
                    editable={true}
                    isSeriesEvent={!!selectedEvent.series_guid}
                    onPerformersChange={refetchSelectedEvent}
                  />
                </div>
              )}

              {/* Logistics Section (hidden for deadline events) */}
              {!selectedEvent.is_deadline && (selectedEvent.ticket_required || selectedEvent.timeoff_required || selectedEvent.travel_required) && (
                <div className="pt-2 border-t">
                  <div className="text-sm font-medium text-muted-foreground mb-2">Logistics</div>
                  <div className="space-y-2">
                    {/* Ticket */}
                    {selectedEvent.ticket_required && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm">
                          <Ticket className="h-4 w-4" />
                          <span>Ticket</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            selectedEvent.ticket_status === 'ready' ? 'bg-green-500/10 text-green-500' :
                            selectedEvent.ticket_status === 'purchased' ? 'bg-yellow-500/10 text-yellow-500' :
                            'bg-red-500/10 text-red-500'
                          }`}>
                            {selectedEvent.ticket_status === 'ready' ? 'Ready' :
                             selectedEvent.ticket_status === 'purchased' ? 'Purchased' : 'Not Purchased'}
                          </span>
                          {selectedEvent.ticket_purchase_date && (
                            <span className="text-xs text-muted-foreground">
                              {formatDateStr(selectedEvent.ticket_purchase_date, { month: 'short', day: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Time Off */}
                    {selectedEvent.timeoff_required && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm">
                          <Briefcase className="h-4 w-4" />
                          <span>Time Off</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            selectedEvent.timeoff_status === 'approved' ? 'bg-green-500/10 text-green-500' :
                            selectedEvent.timeoff_status === 'booked' ? 'bg-yellow-500/10 text-yellow-500' :
                            'bg-red-500/10 text-red-500'
                          }`}>
                            {selectedEvent.timeoff_status === 'approved' ? 'Approved' :
                             selectedEvent.timeoff_status === 'booked' ? 'Booked' : 'Planned'}
                          </span>
                          {selectedEvent.timeoff_booking_date && (
                            <span className="text-xs text-muted-foreground">
                              {formatDateStr(selectedEvent.timeoff_booking_date, { month: 'short', day: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Travel */}
                    {selectedEvent.travel_required && (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm">
                          <Car className="h-4 w-4" />
                          <span>Travel</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            selectedEvent.travel_status === 'booked' ? 'bg-green-500/10 text-green-500' :
                            'bg-red-500/10 text-red-500'
                          }`}>
                            {selectedEvent.travel_status === 'booked' ? 'Booked' : 'Planned'}
                          </span>
                          {selectedEvent.travel_booking_date && (
                            <span className="text-xs text-muted-foreground">
                              {formatDateStr(selectedEvent.travel_booking_date, { month: 'short', day: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Deadline Protection Alert (T038) */}
              {selectedEvent.is_deadline && (
                <Alert className="mt-4 border-amber-500/50 bg-amber-500/10">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <AlertDescription className="text-sm">
                    This is a deadline entry managed automatically.
                    {selectedEvent.series_guid && (
                      <> Edit the parent series to change the deadline.</>
                    )}
                    {!selectedEvent.series_guid && (
                      <> Edit the parent event to change the deadline.</>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
          {/* Edit/Delete buttons hidden for deadline entries (T036-T037) */}
          {selectedEvent && !selectedEvent.is_deadline && (
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={handleEditClick}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button variant="destructive" onClick={handleDeleteClick}>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Event Dialog */}
      <Dialog
        open={createDialogOpen}
        onOpenChange={(open) => !open && setCreateDialogOpen(false)}
      >
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>Create Event</DialogTitle>
            <DialogDescription>
              Add a new event to your calendar.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto pr-2">
            <EventForm
              categories={categories}
              onSubmit={handleCreateSubmit}
              onSubmitSeries={handleCreateSeriesSubmit}
              onCancel={() => setCreateDialogOpen(false)}
              isSubmitting={mutations.loading}
              defaultDate={createDefaultDate}
            />
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Event Dialog */}
      <Dialog
        open={editEvent !== null}
        onOpenChange={(open) => !open && setEditEvent(null)}
      >
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>Edit Event</DialogTitle>
            <DialogDescription>
              Update event details.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto pr-2">
            {editEvent && (
              <EventForm
                event={editEvent}
                categories={categories}
                onSubmit={handleEditSubmit}
                onCancel={() => setEditEvent(null)}
                isSubmitting={mutations.loading}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteEvent !== null}
        onOpenChange={(open) => !open && setDeleteEvent(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Event</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteEvent?.title}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
