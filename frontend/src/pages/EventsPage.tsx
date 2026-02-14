/**
 * Events Page
 *
 * Display and manage calendar events.
 * Calendar view with event management capabilities.
 *
 * Issue #39 - Calendar Events feature (Phases 4 & 5).
 */

import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Pencil, Trash2, MapPin, Building2, Ticket, Briefcase, Car, Calendar, AlertTriangle, BarChart3 } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useCalendar, useEvents, useEventStats, useEventMutations } from '@/hooks/useEvents'
import { useConflicts } from '@/hooks/useConflicts'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { EventCalendar, EventList, EventForm, EventPerformersSection } from '@/components/events'
import { ConflictResolutionPanel } from '@/components/events/ConflictResolutionPanel'
import { TimelinePlanner } from '@/components/events/TimelinePlanner'
import { DateRangePicker } from '@/components/events/DateRangePicker'
import { useDateRange } from '@/hooks/useDateRange'
import { useScoringWeights } from '@/hooks/useScoringWeights'
import { AuditTrailSection } from '@/components/audit'
import { useCategories } from '@/hooks/useCategories'
import type { Event, EventDetail, EventCreateRequest, EventUpdateRequest, EventSeriesCreateRequest, EventPreset } from '@/contracts/api/event-api'

const PRESET_LABELS: Record<EventPreset, { icon: typeof Calendar; label: string }> = {
  upcoming_30d: { icon: Calendar, label: 'Upcoming' },
  needs_tickets: { icon: Ticket, label: 'Needs Tickets' },
  needs_pto: { icon: Briefcase, label: 'Needs PTO' },
  needs_travel: { icon: Car, label: 'Needs Travel' },
}

const VALID_PRESETS: EventPreset[] = ['upcoming_30d', 'needs_tickets', 'needs_pto', 'needs_travel']

/** All view options for the responsive dropdown */
const VIEW_OPTIONS: { value: string; label: string; icon: typeof Calendar }[] = [
  { value: 'calendar', label: 'Calendar', icon: Calendar },
  { value: 'upcoming_30d', label: 'Upcoming', icon: Calendar },
  { value: 'needs_tickets', label: 'Needs Tickets', icon: Ticket },
  { value: 'needs_pto', label: 'Needs PTO', icon: Briefcase },
  { value: 'needs_travel', label: 'Needs Travel', icon: Car },
  { value: 'planner', label: 'Planner', icon: BarChart3 },
]

export default function EventsPage() {
  // URL search params for preset filtering and view mode
  const [searchParams, setSearchParams] = useSearchParams()
  const presetParam = searchParams.get('preset') as EventPreset | null
  const viewParam = searchParams.get('view')
  const activePreset = presetParam && VALID_PRESETS.includes(presetParam) ? presetParam : null
  const viewMode: 'calendar' | 'list' | 'planner' = viewParam === 'planner'
    ? 'planner'
    : activePreset ? 'list' : 'calendar'

  // Calendar state and navigation
  const calendar = useCalendar()
  const {
    events: calendarEvents,
    loading: calendarLoading,
    error: calendarError,
    currentYear,
    currentMonth,
    goToPreviousMonth,
    goToNextMonth,
    goToToday,
    refetch: refetchCalendar
  } = calendar

  // Preset list view
  const {
    events: presetEvents,
    loading: presetLoading,
    error: presetError,
    fetchEvents: fetchPresetEvents
  } = useEvents()

  // Date range for list views (Issue #182, US5)
  const dateRange = useDateRange('range')

  // Progressive rendering: show events in chunks (infinite scroll)
  const PAGE_SIZE = 20
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Reset visible count when events or preset changes
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [presetEvents, activePreset])

  // IntersectionObserver for progressive rendering
  useEffect(() => {
    if (viewMode !== 'list') return
    const sentinel = sentinelRef.current
    if (!sentinel) return

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting && visibleCount < presetEvents.length) {
          setVisibleCount(prev => Math.min(prev + PAGE_SIZE, presetEvents.length))
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [viewMode, visibleCount, presetEvents.length])

  const visiblePresetEvents = useMemo(
    () => presetEvents.slice(0, visibleCount),
    [presetEvents, visibleCount],
  )

  // Scoring weights for planner micro-bars (Issue #208)
  const { settings: scoringWeights } = useScoringWeights()

  // Conflict detection for calendar and planner views
  const { data: conflictData, loading: conflictLoading, detectConflicts } = useConflicts()

  // Fetch conflicts when calendar month changes
  useEffect(() => {
    if (viewMode === 'calendar') {
      // Compute the calendar grid date range (6 weeks around current month)
      const firstOfMonth = new Date(currentYear, currentMonth - 1, 1)
      const startDayOfWeek = firstOfMonth.getDay()
      const gridStart = new Date(currentYear, currentMonth - 1, 1 - startDayOfWeek)
      const gridEnd = new Date(gridStart)
      gridEnd.setDate(gridEnd.getDate() + 41) // 42 days total

      const fmt = (d: Date) => {
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${y}-${m}-${day}`
      }

      detectConflicts(fmt(gridStart), fmt(gridEnd)).catch(() => {
        // Silently ignore — conflict indicators just won't show
      })
    }
  }, [viewMode, currentYear, currentMonth, detectConflicts])

  // Fetch conflicts for planner view (uses date range picker)
  useEffect(() => {
    if (viewMode === 'planner') {
      detectConflicts(dateRange.range.startDate, dateRange.range.endDate).catch(() => {})
    }
  }, [viewMode, dateRange.range.startDate, dateRange.range.endDate, detectConflicts])

  // Refetch conflicts (used after resolution)
  const refetchConflicts = useCallback(() => {
    if (viewMode === 'calendar') {
      const firstOfMonth = new Date(currentYear, currentMonth - 1, 1)
      const startDayOfWeek = firstOfMonth.getDay()
      const gridStart = new Date(currentYear, currentMonth - 1, 1 - startDayOfWeek)
      const gridEnd = new Date(gridStart)
      gridEnd.setDate(gridEnd.getDate() + 41)

      const fmt = (d: Date) => {
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${y}-${m}-${day}`
      }

      detectConflicts(fmt(gridStart), fmt(gridEnd)).catch(() => {})
    } else if (viewMode === 'planner') {
      detectConflicts(dateRange.range.startDate, dateRange.range.endDate).catch(() => {})
    }
  }, [viewMode, currentYear, currentMonth, dateRange.range.startDate, dateRange.range.endDate, detectConflicts])

  // Fetch preset events when preset or date range changes
  useEffect(() => {
    if (activePreset) {
      fetchPresetEvents({
        preset: activePreset,
        start_date: dateRange.range.startDate,
        end_date: dateRange.range.endDate,
      })
    }
  }, [activePreset, dateRange.range.startDate, dateRange.range.endDate, fetchPresetEvents])

  // Error from whichever view is active
  const error = viewMode === 'list' ? presetError : calendarError

  const refetch = useCallback(async () => {
    if (viewMode === 'list' && activePreset) {
      await fetchPresetEvents({
        preset: activePreset,
        start_date: dateRange.range.startDate,
        end_date: dateRange.range.endDate,
      })
    } else if (viewMode === 'planner') {
      await detectConflicts(dateRange.range.startDate, dateRange.range.endDate).catch(() => {})
    } else {
      await refetchCalendar()
    }
  }, [viewMode, activePreset, dateRange.range.startDate, dateRange.range.endDate, fetchPresetEvents, detectConflicts, refetchCalendar])

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useEventStats()
  const { setStats } = useHeaderStats()

  // Categories for event form
  const { categories } = useCategories(true)

  // Event mutations
  const mutations = useEventMutations()

  // Preset navigation handlers
  const handlePresetClick = (preset: EventPreset) => {
    setSearchParams({ preset })
  }

  const handleShowCalendar = () => {
    setSearchParams({})
  }

  const handleShowPlanner = () => {
    setSearchParams({ view: 'planner' })
  }

  // Active view value for responsive dropdown
  const activeView = viewMode === 'planner' ? 'planner' : activePreset ?? 'calendar'

  // Handle view change from responsive dropdown
  const handleViewChange = (value: string) => {
    if (value === 'calendar') {
      handleShowCalendar()
    } else if (value === 'planner') {
      handleShowPlanner()
    } else {
      handlePresetClick(value as EventPreset)
    }
  }

  // Update header stats — planner-specific KPIs when planner is active
  useEffect(() => {
    if (viewMode === 'planner' && conflictData) {
      const scoredEvents = conflictData.scored_events ?? []
      const avgQuality = scoredEvents.length > 0
        ? Math.round(scoredEvents.reduce((sum, e) => sum + e.scores.composite, 0) / scoredEvents.length)
        : 0
      setStats([
        { label: 'Conflicts', value: conflictData.summary.total_groups.toLocaleString() },
        { label: 'Unresolved', value: conflictData.summary.unresolved.toLocaleString() },
        { label: 'Events Scored', value: scoredEvents.length.toLocaleString() },
        { label: 'Avg Quality', value: `${avgQuality}` },
      ])
    } else if (stats) {
      setStats([
        { label: 'Total Events', value: stats.total_count.toLocaleString() },
        { label: 'Upcoming', value: stats.upcoming_count.toLocaleString() },
        { label: 'This Month', value: stats.this_month_count.toLocaleString() },
        { label: 'Attended', value: stats.attended_count.toLocaleString() }
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [viewMode, conflictData, stats, setStats])

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
    const dayEvents = calendarEvents.filter(e => e.event_date === dateString)

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
    refetchConflicts()
  }

  // Handle series create submit
  const handleCreateSeriesSubmit = async (data: EventSeriesCreateRequest) => {
    await mutations.createEventSeries(data)
    setCreateDialogOpen(false)
    await refetch()
    await refetchStats()
    refetchConflicts()
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
      refetchConflicts()
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
      refetchConflicts()
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

  // Day-scoped conflict groups: filter edges touching the selected day,
  // collect only referenced events, and recompute status per day.
  const selectedDayConflicts = useMemo(() => {
    if (!selectedDay || !conflictData) return []
    const dateStr = formatDateString(selectedDay.date)
    const dayGroups: typeof conflictData.conflict_groups = []

    for (const group of conflictData.conflict_groups) {
      const eventByGuid = new Map(group.events.map(e => [e.guid, e]))

      // Filter edges where at least one event is on the selected day
      const dayEdges = group.edges.filter(edge => {
        const a = eventByGuid.get(edge.event_a_guid)
        const b = eventByGuid.get(edge.event_b_guid)
        return a?.event_date === dateStr || b?.event_date === dateStr
      })

      if (dayEdges.length === 0) continue

      // Collect events referenced by day-scoped edges
      const referencedGuids = new Set<string>()
      for (const edge of dayEdges) {
        referencedGuids.add(edge.event_a_guid)
        referencedGuids.add(edge.event_b_guid)
      }
      const dayEvents = group.events.filter(e => referencedGuids.has(e.guid))

      // Recompute status from day-scoped edges (same logic as backend)
      const skippedGuids = new Set(
        dayEvents.filter(e => e.attendance === 'skipped').map(e => e.guid),
      )
      const unresolvedEdgeCount = dayEdges.filter(
        e => !skippedGuids.has(e.event_a_guid) && !skippedGuids.has(e.event_b_guid),
      ).length

      const status: 'resolved' | 'partially_resolved' | 'unresolved' =
        unresolvedEdgeCount === 0
          ? 'resolved'
          : unresolvedEdgeCount < dayEdges.length
            ? 'partially_resolved'
            : 'unresolved'

      dayGroups.push({
        group_id: group.group_id,
        status,
        events: dayEvents,
        edges: dayEdges,
      })
    }

    return dayGroups
  }, [selectedDay, conflictData])

  // Count unresolved edges across all day-scoped groups (not groups)
  const unresolvedConflictCount = selectedDayConflicts.reduce((count, g) => {
    const skippedGuids = new Set(
      g.events.filter(e => e.attendance === 'skipped').map(e => e.guid),
    )
    return count + g.edges.filter(
      e => !skippedGuids.has(e.event_a_guid) && !skippedGuids.has(e.event_b_guid),
    ).length
  }, 0)

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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-4">
        {/* Mobile: dropdown selector */}
        <div className="md:hidden">
          <Select value={activeView} onValueChange={handleViewChange}>
            <SelectTrigger>
              <SelectValue>
                {(() => {
                  const opt = VIEW_OPTIONS.find(o => o.value === activeView)
                  if (!opt) return null
                  const Icon = opt.icon
                  return (
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {opt.label}
                    </span>
                  )
                })()}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {VIEW_OPTIONS.map(opt => {
                const Icon = opt.icon
                return (
                  <SelectItem key={opt.value} value={opt.value}>
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {opt.label}
                    </span>
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Desktop: button bar */}
        <div className="hidden md:flex items-center gap-2 flex-wrap">
          {(Object.entries(PRESET_LABELS) as [EventPreset, { icon: typeof Calendar; label: string }][]).map(
            ([preset, { icon: PresetIcon, label }]) => (
              <Button
                key={preset}
                variant={activePreset === preset ? 'default' : 'outline'}
                size="sm"
                onClick={() => handlePresetClick(preset)}
              >
                <PresetIcon className="h-4 w-4 mr-1.5" />
                {label}
              </Button>
            )
          )}
          <Button
            variant={viewMode === 'planner' ? 'default' : 'outline'}
            size="sm"
            onClick={handleShowPlanner}
          >
            <BarChart3 className="h-4 w-4 mr-1.5" />
            Planner
          </Button>
          {(activePreset || viewMode === 'planner') && (
            <Button variant="ghost" size="sm" onClick={handleShowCalendar}>
              Show Calendar
            </Button>
          )}
        </div>

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
      {viewMode === 'calendar' && (
        <div className="flex-1 min-h-0">
          <EventCalendar
            events={calendarEvents}
            year={currentYear}
            month={currentMonth}
            loading={calendarLoading}
            conflicts={conflictData}
            onPreviousMonth={goToPreviousMonth}
            onNextMonth={goToNextMonth}
            onToday={goToToday}
            onEventClick={handleEventClick}
            onDayClick={handleDayClick}
            className="h-full"
          />
        </div>
      )}

      {/* Preset List View */}
      {viewMode === 'list' && (
        <div className="flex-1 min-h-0 flex flex-col">
          {/* Date Range Picker (Issue #182, US5) */}
          <DateRangePicker
            preset={dateRange.preset}
            range={dateRange.range}
            customStart={dateRange.customStart}
            customEnd={dateRange.customEnd}
            onPresetChange={dateRange.setPreset}
            onCustomRangeChange={dateRange.setCustomRange}
            className="mb-3"
          />

          {presetLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <div className="overflow-y-auto flex-1 min-h-0">
              <EventList
                events={visiblePresetEvents}
                onEventClick={handleEventClick}
                emptyMessage="No events match this filter in the selected date range"
                showDate
              />
              {/* Infinite scroll sentinel */}
              {visibleCount < presetEvents.length && (
                <div ref={sentinelRef} className="flex items-center justify-center py-4">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary" />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Planner View (Issue #182, US6) */}
      {viewMode === 'planner' && (
        <div className="flex-1 min-h-0 flex flex-col">
          <DateRangePicker
            preset={dateRange.preset}
            range={dateRange.range}
            customStart={dateRange.customStart}
            customEnd={dateRange.customEnd}
            onPresetChange={dateRange.setPreset}
            onCustomRangeChange={dateRange.setCustomRange}
            className="mb-3"
          />

          <div className="overflow-y-auto flex-1 min-h-0">
            <TimelinePlanner
              events={conflictData?.scored_events ?? []}
              conflicts={conflictData}
              loading={conflictLoading}
              categories={categories.map(c => ({ guid: c.guid, name: c.name, icon: c.icon, color: c.color }))}
              scoringWeights={scoringWeights ?? undefined}
              onResolved={refetchConflicts}
            />
          </div>
        </div>
      )}

      {/* Day Detail Dialog */}
      <Dialog
        open={selectedDay !== null}
        onOpenChange={(open) => !open && setSelectedDay(null)}
      >
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>
              {selectedDay && formatDisplayDate(selectedDay.date)}
            </DialogTitle>
            <DialogDescription>
              {selectedDay?.events.length} event{selectedDay?.events.length !== 1 ? 's' : ''} on this day
            </DialogDescription>
          </DialogHeader>

          {/* Show tabs when conflicts exist, plain list otherwise */}
          {selectedDayConflicts.length > 0 ? (
            <Tabs defaultValue="events" className="w-full min-h-0 flex flex-col flex-1">
              <TabsList className="w-full flex-shrink-0">
                <TabsTrigger value="events" className="flex-1">Events</TabsTrigger>
                <TabsTrigger value="conflicts" className="flex-1 gap-1.5">
                  Conflicts
                  {unresolvedConflictCount > 0 && (
                    <span className="inline-flex items-center justify-center h-5 min-w-5 px-1 rounded-full text-[10px] font-bold bg-amber-500 text-white">
                      {unresolvedConflictCount}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>
              <TabsContent value="events" className="overflow-y-auto min-h-0">
                {selectedDay && (
                  <EventList
                    events={selectedDay.events}
                    onEventClick={handleEventClick}
                  />
                )}
              </TabsContent>
              <TabsContent value="conflicts" className="overflow-y-auto min-h-0">
                <ConflictResolutionPanel
                  groups={selectedDayConflicts}
                  referenceDate={selectedDay ? formatDateString(selectedDay.date) : undefined}
                  onResolved={() => {
                    refetchConflicts()
                    refetch()
                  }}
                />
              </TabsContent>
            </Tabs>
          ) : (
            <div className="overflow-y-auto min-h-0 flex-1">
              {selectedDay && (
                <EventList
                  events={selectedDay.events}
                  onEventClick={handleEventClick}
                />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Event Detail Dialog */}
      <Dialog
        open={selectedEvent !== null}
        onOpenChange={(open) => !open && setSelectedEvent(null)}
      >
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
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
            <div className="space-y-4 pt-4 overflow-y-auto flex-1">
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

              {/* Audit Trail (Issue #120) */}
              <AuditTrailSection audit={selectedEvent.audit} />
            </div>
          )}
          {/* Edit/Delete buttons hidden for deadline entries (T036-T037) */}
          {selectedEvent && !selectedEvent.is_deadline && (
            <DialogFooter className="flex-shrink-0 gap-2 sm:gap-0">
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
