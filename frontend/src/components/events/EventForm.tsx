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
import { cn } from '@/lib/utils'
import type {
  EventDetail,
  EventCreateRequest,
  EventUpdateRequest,
  EventSeriesCreateRequest
} from '@/contracts/api/event-api'
import type { Category } from '@/contracts/api/category-api'

// ============================================================================
// Form Schema
// ============================================================================

const eventFormSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255),
  description: z.string().optional(),
  category_guid: z.string().min(1, 'Category is required'),
  start_time: z.string().optional(),
  end_time: z.string().optional(),
  is_all_day: z.boolean(),
  status: z.enum(['future', 'confirmed', 'completed', 'cancelled']),
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

  // Initialize form
  const form = useForm<EventFormValues>({
    resolver: zodResolver(eventFormSchema),
    defaultValues: {
      title: '',
      description: '',
      category_guid: '',
      start_time: '',
      end_time: '',
      is_all_day: false,
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
        start_time: event.start_time?.slice(0, 5) || '', // HH:MM
        end_time: event.end_time?.slice(0, 5) || '', // HH:MM
        is_all_day: event.is_all_day,
        status: event.status,
        attendance: event.attendance,
      })
      setSelectedDate(event.event_date)
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

  // Handle form submission
  const handleSubmit = async (values: EventFormValues) => {
    if (mode === 'series' && !isEditMode) {
      // Series creation
      if (seriesDates.length < 2) {
        return // Validation will show error
      }

      const seriesData: EventSeriesCreateRequest = {
        title: values.title,
        description: values.description || undefined,
        category_guid: values.category_guid,
        event_dates: seriesDates,
        start_time: values.is_all_day ? undefined : (values.start_time || undefined),
        end_time: values.is_all_day ? undefined : (values.end_time || undefined),
        is_all_day: values.is_all_day,
        ticket_required: false,
        timeoff_required: false,
        travel_required: false,
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
        event_date: selectedDate,
        start_time: values.is_all_day ? null : (values.start_time || null),
        end_time: values.is_all_day ? null : (values.end_time || null),
        is_all_day: values.is_all_day,
        status: values.status,
        attendance: values.attendance,
      }

      await onSubmit(data)
    }
  }

  // Watch all-day state to show/hide time fields
  const isAllDay = form.watch('is_all_day')

  // Validation for series mode
  const seriesError = mode === 'series' && seriesDates.length < 2

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
                  {categories.map(category => (
                    <SelectItem key={category.guid} value={category.guid}>
                      <span className="flex items-center gap-2">
                        {category.color && (
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                        )}
                        {category.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
                      <SelectItem value="future">Future</SelectItem>
                      <SelectItem value="confirmed">Confirmed</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
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
