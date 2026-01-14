/**
 * Event Form Component
 *
 * Form for creating and editing calendar events.
 * Supports both single events and multi-day series.
 * Issue #39 - Calendar Events feature (Phase 5)
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, X, CalendarDays, Calendar as CalendarIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { TimezoneCombobox } from '@/components/ui/timezone-combobox'
import { LocationPicker } from '@/components/events/LocationPicker'
import { OrganizerPicker } from '@/components/events/OrganizerPicker'
import { LogisticsSection, type LogisticsData } from '@/components/events/LogisticsSection'
import { useEventStatuses } from '@/hooks/useConfig'
import { cn } from '@/lib/utils'
import type {
  EventDetail,
  EventCreateRequest,
  EventUpdateRequest,
  EventSeriesCreateRequest
} from '@/contracts/api/event-api'
import type { Category } from '@/contracts/api/category-api'
import type { Location } from '@/contracts/api/location-api'
import type { Organizer } from '@/contracts/api/organizer-api'

// ============================================================================
// Form Schema
// ============================================================================

const eventFormSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255),
  description: z.string().optional(),
  category_guid: z.string().min(1, 'Category is required'),
  location_guid: z.string().optional().nullable(),
  organizer_guid: z.string().optional().nullable(),
  start_time: z.string().optional(),
  end_time: z.string().optional(),
  is_all_day: z.boolean(),
  input_timezone: z.string().optional(),
  status: z.string().min(1, 'Status is required'),
  attendance: z.enum(['planned', 'attended', 'skipped']),
})

type EventFormValues = z.infer<typeof eventFormSchema>

// ============================================================================
// Types
// ============================================================================

type EventMode = 'single' | 'series'

interface EventFormProps {
  /** Event to edit (null for create mode) */
  event?: EventDetail | null
  /** Available categories for selection */
  categories: Category[]
  /** Called when single event form is submitted */
  onSubmit: (data: EventCreateRequest | EventUpdateRequest) => Promise<void>
  /** Called when series form is submitted */
  onSubmitSeries?: (data: EventSeriesCreateRequest) => Promise<void>
  /** Called when cancel is clicked */
  onCancel: () => void
  /** Whether form is submitting */
  isSubmitting?: boolean
  /** Pre-selected date for new events */
  defaultDate?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format date for display
 */
function formatDateDisplay(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric'
  })
}

/**
 * Sort dates chronologically
 */
function sortDates(dates: string[]): string[] {
  return [...dates].sort((a, b) => a.localeCompare(b))
}

// ============================================================================
// Event Form Component
// ============================================================================

export const EventForm = ({
  event,
  categories,
  onSubmit,
  onSubmitSeries,
  onCancel,
  isSubmitting = false,
  defaultDate
}: EventFormProps) => {
  const isEditMode = !!event

  // Fetch event statuses from config
  const { statuses: eventStatuses } = useEventStatuses()

  // Event mode (single vs series) - only for create mode
  const [mode, setMode] = useState<EventMode>('single')

  // Selected dates for single event or series
  const [selectedDate, setSelectedDate] = useState<string>(
    defaultDate || new Date().toISOString().split('T')[0]
  )
  const [seriesDates, setSeriesDates] = useState<string[]>(
    defaultDate ? [defaultDate] : []
  )

  // Date input for adding to series
  const [dateInput, setDateInput] = useState<string>('')

  // Selected location (for LocationPicker display)
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)

  // Selected organizer (for OrganizerPicker display)
  const [selectedOrganizer, setSelectedOrganizer] = useState<Organizer | null>(null)

  // Logistics data
  const [logistics, setLogistics] = useState<LogisticsData>({
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
  })

  // Initialize form
  const form = useForm<EventFormValues>({
    resolver: zodResolver(eventFormSchema),
    defaultValues: {
      title: '',
      description: '',
      category_guid: '',
      location_guid: null,
      organizer_guid: null,
      start_time: '',
      end_time: '',
      is_all_day: false,
      input_timezone: '',
      status: 'future',
      attendance: 'planned',
    }
  })

  // Populate form when editing
  useEffect(() => {
    if (event) {
      form.reset({
        title: event.title,
        description: event.description || '',
        category_guid: event.category?.guid || '',
        location_guid: event.location?.guid || null,
        organizer_guid: event.organizer?.guid || null,
        start_time: event.start_time?.slice(0, 5) || '', // HH:MM
        end_time: event.end_time?.slice(0, 5) || '', // HH:MM
        is_all_day: event.is_all_day,
        input_timezone: event.input_timezone || '',
        status: event.status,
        attendance: event.attendance,
      })
      setSelectedDate(event.event_date)
      // Set location for picker display (convert summary to partial Location)
      if (event.location) {
        setSelectedLocation({
          guid: event.location.guid,
          name: event.location.name,
          city: event.location.city,
          country: event.location.country,
          timezone: event.location.timezone,
          // Remaining fields are not available from summary, use defaults
          address: null,
          state: null,
          postal_code: null,
          latitude: null,
          longitude: null,
          category: event.category ? {
            guid: event.category.guid,
            name: event.category.name,
            icon: event.category.icon || null,
            color: event.category.color || null,
          } : { guid: '', name: '', icon: null, color: null },
          rating: null,
          timeoff_required_default: false,
          travel_required_default: false,
          notes: null,
          is_known: true,
          created_at: '',
          updated_at: '',
        })
      }
      // Set organizer for picker display (convert summary to partial Organizer)
      if (event.organizer) {
        setSelectedOrganizer({
          guid: event.organizer.guid,
          name: event.organizer.name,
          website: null,
          category: event.category ? {
            guid: event.category.guid,
            name: event.category.name,
            icon: event.category.icon || null,
            color: event.category.color || null,
          } : { guid: '', name: '', icon: null, color: null },
          rating: null,
          ticket_required_default: false,
          notes: null,
          created_at: '',
          updated_at: '',
        })
      }
      // Set logistics data from event
      // deadline_date and deadline_time are synced from series to all events
      setLogistics({
        ticket_required: event.ticket_required,
        ticket_status: event.ticket_status,
        ticket_purchase_date: event.ticket_purchase_date,
        timeoff_required: event.timeoff_required,
        timeoff_status: event.timeoff_status,
        timeoff_booking_date: event.timeoff_booking_date,
        travel_required: event.travel_required,
        travel_status: event.travel_status,
        travel_booking_date: event.travel_booking_date,
        deadline_date: event.deadline_date,
        deadline_time: event.deadline_time,
      })
    }
  }, [event, form])

  // Add date to series
  const addDateToSeries = () => {
    if (dateInput && !seriesDates.includes(dateInput)) {
      setSeriesDates(sortDates([...seriesDates, dateInput]))
      setDateInput('')
    }
  }

  // Remove date from series
  const removeDateFromSeries = (dateToRemove: string) => {
    setSeriesDates(seriesDates.filter(d => d !== dateToRemove))
  }

  // Handle location selection
  const handleLocationChange = (location: Location | null) => {
    setSelectedLocation(location)
    form.setValue('location_guid', location?.guid || null)
  }

  // Handle timezone suggestion from location
  const handleTimezoneHint = (timezone: string) => {
    // Only suggest if no timezone is set
    const currentTimezone = form.getValues('input_timezone')
    if (!currentTimezone) {
      form.setValue('input_timezone', timezone)
    }
  }

  // Handle organizer selection
  const handleOrganizerChange = (organizer: Organizer | null) => {
    setSelectedOrganizer(organizer)
    form.setValue('organizer_guid', organizer?.guid || null)
  }

  // Handle form submission
  const handleSubmit = async (values: EventFormValues) => {
    // Normalize timezone value (empty string -> undefined/null)
    const timezone = values.input_timezone || undefined

    if (mode === 'series' && !isEditMode) {
      // Series creation
      if (seriesDates.length < 2) {
        return // Validation will show error
      }

      const seriesData: EventSeriesCreateRequest = {
        title: values.title,
        description: values.description || undefined,
        category_guid: values.category_guid,
        location_guid: values.location_guid || undefined,
        organizer_guid: values.organizer_guid || undefined,
        event_dates: seriesDates,
        start_time: values.is_all_day ? undefined : (values.start_time || undefined),
        end_time: values.is_all_day ? undefined : (values.end_time || undefined),
        is_all_day: values.is_all_day,
        input_timezone: values.is_all_day ? undefined : timezone,
        ticket_required: logistics.ticket_required ?? false,
        timeoff_required: logistics.timeoff_required ?? false,
        travel_required: logistics.travel_required ?? false,
        deadline_date: logistics.deadline_date || undefined,
        deadline_time: logistics.deadline_time || undefined,
        status: values.status,
        attendance: values.attendance,
      }

      if (onSubmitSeries) {
        await onSubmitSeries(seriesData)
      }
    } else {
      // Single event creation or edit
      const data: EventCreateRequest | EventUpdateRequest = {
        title: values.title,
        description: values.description || null,
        category_guid: values.category_guid,
        location_guid: values.location_guid || null,
        organizer_guid: values.organizer_guid || null,
        event_date: selectedDate,
        start_time: values.is_all_day ? null : (values.start_time || null),
        end_time: values.is_all_day ? null : (values.end_time || null),
        is_all_day: values.is_all_day,
        input_timezone: values.is_all_day ? null : (timezone || null),
        status: values.status,
        attendance: values.attendance,
        // Logistics
        ticket_required: logistics.ticket_required,
        ticket_status: logistics.ticket_status,
        ticket_purchase_date: logistics.ticket_purchase_date,
        timeoff_required: logistics.timeoff_required,
        timeoff_status: logistics.timeoff_status,
        timeoff_booking_date: logistics.timeoff_booking_date,
        travel_required: logistics.travel_required,
        travel_status: logistics.travel_status,
        travel_booking_date: logistics.travel_booking_date,
        deadline_date: logistics.deadline_date,
        deadline_time: logistics.deadline_time,
      }

      await onSubmit(data)
    }
  }

  // Watch all-day state to show/hide time fields
  const isAllDay = form.watch('is_all_day')

  // Watch category for LocationPicker filtering
  const selectedCategoryGuid = form.watch('category_guid')

  // Clear location when category changes (locations are category-specific)
  useEffect(() => {
    // Only clear if we're not in initial load (when event is being populated)
    if (!event && selectedLocation && selectedLocation.category?.guid !== selectedCategoryGuid) {
      setSelectedLocation(null)
      form.setValue('location_guid', null)
    }
  }, [selectedCategoryGuid, selectedLocation, event, form])

  // Clear organizer when category changes (organizers are category-specific)
  useEffect(() => {
    // Only clear if we're not in initial load (when event is being populated)
    if (!event && selectedOrganizer && selectedOrganizer.category?.guid !== selectedCategoryGuid) {
      setSelectedOrganizer(null)
      form.setValue('organizer_guid', null)
    }
  }, [selectedCategoryGuid, selectedOrganizer, event, form])

  // Validation for series mode
  const seriesError = mode === 'series' && seriesDates.length < 2

  // Filter categories: only show active categories when creating, all when editing
  const availableCategories = isEditMode
    ? categories
    : categories.filter(c => c.is_active)

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        {/* Mode Toggle (only in create mode) */}
        {!isEditMode && onSubmitSeries && (
          <div className="flex gap-2 p-1 bg-muted rounded-lg">
            <button
              type="button"
              onClick={() => setMode('single')}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-colors',
                mode === 'single'
                  ? 'bg-background shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <CalendarIcon className="h-4 w-4" />
              Single Event
            </button>
            <button
              type="button"
              onClick={() => setMode('series')}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-colors',
                mode === 'series'
                  ? 'bg-background shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <CalendarDays className="h-4 w-4" />
              Event Series
            </button>
          </div>
        )}

        {/* Title */}
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Title</FormLabel>
              <FormControl>
                <Input placeholder="Event title" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Description */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Event description (optional)"
                  className="resize-none"
                  rows={3}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Category */}
        <FormField
          control={form.control}
          name="category_guid"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Category</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {availableCategories.map(category => (
                    <SelectItem key={category.guid} value={category.guid}>
                      <span className="flex items-center gap-2">
                        {category.color && (
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                        )}
                        {category.name}
                        {!category.is_active && (
                          <span className="text-muted-foreground">(inactive)</span>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Location */}
        <FormField
          control={form.control}
          name="location_guid"
          render={() => (
            <FormItem>
              <FormLabel>Location</FormLabel>
              <FormControl>
                <LocationPicker
                  categoryGuid={selectedCategoryGuid || null}
                  value={selectedLocation}
                  onChange={handleLocationChange}
                  onTimezoneHint={handleTimezoneHint}
                  placeholder={selectedCategoryGuid ? 'Select or enter location...' : 'Select a category first'}
                  disabled={!selectedCategoryGuid}
                />
              </FormControl>
              <FormDescription>
                Select a known location or enter a new address
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Organizer */}
        <FormField
          control={form.control}
          name="organizer_guid"
          render={() => (
            <FormItem>
              <FormLabel>Organizer</FormLabel>
              <FormControl>
                <OrganizerPicker
                  categoryGuid={selectedCategoryGuid || null}
                  value={selectedOrganizer}
                  onChange={handleOrganizerChange}
                  placeholder={selectedCategoryGuid ? 'Select organizer...' : 'Select a category first'}
                  disabled={!selectedCategoryGuid}
                />
              </FormControl>
              <FormDescription>
                Select the event organizer (optional)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Date Selection - Single Mode */}
        {(mode === 'single' || isEditMode) && (
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              Date
            </label>
            <DatePicker
              value={selectedDate}
              onChange={(date) => setSelectedDate(date || '')}
              placeholder="Select event date"
            />
          </div>
        )}

        {/* Date Selection - Series Mode */}
        {mode === 'series' && !isEditMode && (
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              Dates
            </label>
            <p className="text-sm text-muted-foreground">
              Add at least 2 dates for your event series. Each date will create a separate event.
            </p>

            {/* Date Input */}
            <div className="flex gap-2">
              <div className="flex-1">
                <DatePicker
                  value={dateInput}
                  onChange={(date) => setDateInput(date || '')}
                  placeholder="Select a date to add"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={addDateToSeries}
                disabled={!dateInput || seriesDates.includes(dateInput)}
              >
                Add Date
              </Button>
            </div>

            {/* Selected Dates */}
            {seriesDates.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {seriesDates.map((date, index) => (
                  <Badge
                    key={date}
                    variant="secondary"
                    className="pl-2 pr-1 py-1 flex items-center gap-1"
                  >
                    <span className="text-xs text-muted-foreground mr-1">
                      {index + 1}.
                    </span>
                    {formatDateDisplay(date)}
                    <button
                      type="button"
                      onClick={() => removeDateFromSeries(date)}
                      className="ml-1 hover:bg-muted rounded p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}

            {/* Series validation error */}
            {seriesError && (
              <p className="text-sm text-destructive mt-1">
                Event series requires at least 2 dates
              </p>
            )}
          </div>
        )}

        {/* All Day Checkbox */}
        <FormField
          control={form.control}
          name="is_all_day"
          render={({ field }) => (
            <FormItem className="flex flex-row items-start space-x-3 space-y-0">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel>All day event</FormLabel>
                <FormDescription>
                  Event spans the entire day without specific times
                </FormDescription>
              </div>
            </FormItem>
          )}
        />

        {/* Time Fields (hidden when all-day) */}
        {!isAllDay && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="start_time"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Start Time</FormLabel>
                    <FormControl>
                      <Input type="time" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="end_time"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>End Time</FormLabel>
                    <FormControl>
                      <Input type="time" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Timezone Selector */}
            <FormField
              control={form.control}
              name="input_timezone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Timezone</FormLabel>
                  <FormControl>
                    <TimezoneCombobox
                      value={field.value || ''}
                      onChange={field.onChange}
                      placeholder="Select timezone (optional)"
                    />
                  </FormControl>
                  <FormDescription>
                    Timezone where the event takes place
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </>
        )}

        {/* Status and Attendance */}
        <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {eventStatuses.map(status => (
                        <SelectItem key={status.key} value={status.key}>
                          {status.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="attendance"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Attendance</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select attendance" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="planned">Planned</SelectItem>
                      <SelectItem value="attended">Attended</SelectItem>
                      <SelectItem value="skipped">Skipped</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
        </div>

        {/* Workflow Deadline */}
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            Workflow Deadline
          </label>
          <div className="flex gap-2">
            <div className="flex-1">
              <DatePicker
                value={logistics.deadline_date ?? ''}
                onChange={(date) => setLogistics({ ...logistics, deadline_date: date || null, deadline_time: date ? logistics.deadline_time : null })}
                placeholder="Select deadline date"
                clearable
              />
            </div>
            <div className="w-24">
              <Input
                type="time"
                value={logistics.deadline_time ?? ''}
                onChange={(e) => setLogistics({ ...logistics, deadline_time: e.target.value || null })}
                placeholder="Time"
              />
            </div>
          </div>
          <p className="text-[0.8rem] text-muted-foreground">
            Complete images processing by this date
          </p>
        </div>

        {/* Logistics Section */}
        <div className="pt-2 border-t">
          <LogisticsSection
            data={logistics}
            onChange={setLogistics}
            defaultOpen={isEditMode && (
              logistics.ticket_required ||
              logistics.timeoff_required ||
              logistics.travel_required
            ) as boolean}
          />
        </div>

        {/* Form Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting || (mode === 'series' && !isEditMode && seriesDates.length < 2)}
          >
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEditMode
              ? 'Save Changes'
              : mode === 'series'
                ? `Create Series (${seriesDates.length} events)`
                : 'Create Event'
            }
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default EventForm
