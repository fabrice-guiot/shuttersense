/**
 * Logistics Section Component
 *
 * Collapsible section for managing event logistics:
 * - Ticket tracking with status and purchase date
 * - Time-off tracking with status and booking date
 * - Travel tracking with status and booking date
 * - Workflow deadline date
 *
 * Issue #39 - Calendar Events feature (Phase 10)
 */

import { useState } from 'react'
import { ChevronDown, ChevronUp, Ticket, Briefcase, Car } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { TicketStatus, TimeoffStatus, TravelStatus } from '@/contracts/api/event-api'

// ============================================================================
// Status Options Configuration
// ============================================================================

interface StatusOption<T> {
  value: T
  label: string
  color: 'red' | 'yellow' | 'green'
}

const TICKET_STATUS_OPTIONS: StatusOption<TicketStatus>[] = [
  { value: 'not_purchased', label: 'Not Purchased', color: 'red' },
  { value: 'purchased', label: 'Purchased', color: 'yellow' },
  { value: 'ready', label: 'Ready', color: 'green' },
]

const TIMEOFF_STATUS_OPTIONS: StatusOption<TimeoffStatus>[] = [
  { value: 'planned', label: 'Planned', color: 'red' },
  { value: 'booked', label: 'Booked', color: 'yellow' },
  { value: 'approved', label: 'Approved', color: 'green' },
]

const TRAVEL_STATUS_OPTIONS: StatusOption<TravelStatus>[] = [
  { value: 'planned', label: 'Planned', color: 'red' },
  { value: 'booked', label: 'Booked', color: 'green' },
]

// ============================================================================
// Status Color Indicator
// ============================================================================

function StatusIndicator({ color }: { color: 'red' | 'yellow' | 'green' }) {
  return (
    <span
      className={cn(
        'inline-block w-2 h-2 rounded-full mr-2',
        color === 'red' && 'bg-red-500',
        color === 'yellow' && 'bg-yellow-500',
        color === 'green' && 'bg-green-500'
      )}
    />
  )
}

// ============================================================================
// Types
// ============================================================================

export interface LogisticsData {
  ticket_required: boolean | null
  ticket_status: TicketStatus | null
  ticket_purchase_date: string | null
  timeoff_required: boolean | null
  timeoff_status: TimeoffStatus | null
  timeoff_booking_date: string | null
  travel_required: boolean | null
  travel_status: TravelStatus | null
  travel_booking_date: string | null
  deadline_date: string | null
}

export interface LogisticsSectionProps {
  /** Current logistics data */
  data: LogisticsData
  /** Called when any logistics field changes */
  onChange: (data: LogisticsData) => void
  /** Whether to show the section expanded by default */
  defaultOpen?: boolean
  /** Disable all inputs */
  disabled?: boolean
}

// ============================================================================
// Component
// ============================================================================

export function LogisticsSection({
  data,
  onChange,
  defaultOpen = false,
  disabled = false,
}: LogisticsSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  // Count active logistics for summary
  const activeCount = [
    data.ticket_required,
    data.timeoff_required,
    data.travel_required,
  ].filter(Boolean).length

  // Update a single field
  const updateField = <K extends keyof LogisticsData>(
    field: K,
    value: LogisticsData[K]
  ) => {
    onChange({ ...data, [field]: value })
  }

  // Toggle required checkbox and set default status
  const toggleRequired = (
    field: 'ticket_required' | 'timeoff_required' | 'travel_required',
    statusField: 'ticket_status' | 'timeoff_status' | 'travel_status',
    defaultStatus: TicketStatus | TimeoffStatus | TravelStatus
  ) => {
    const newRequired = !data[field]
    const newData = { ...data, [field]: newRequired }
    // Set default status when enabling, clear when disabling
    if (newRequired && !data[statusField]) {
      ;(newData as any)[statusField] = defaultStatus
    } else if (!newRequired) {
      ;(newData as any)[statusField] = null
    }
    onChange(newData)
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          type="button"
          className="w-full justify-between p-0 h-auto hover:bg-transparent"
          disabled={disabled}
        >
          <div className="flex items-center gap-2">
            <span className="font-medium">Logistics</span>
            {activeCount > 0 && (
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
                {activeCount} active
              </span>
            )}
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-4 space-y-4">
        {/* Ticket Section */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Checkbox
              id="ticket_required"
              checked={data.ticket_required ?? false}
              onCheckedChange={() =>
                toggleRequired('ticket_required', 'ticket_status', 'not_purchased')
              }
              disabled={disabled}
            />
            <Label
              htmlFor="ticket_required"
              className="flex items-center gap-2 cursor-pointer font-medium"
            >
              <Ticket className="h-4 w-4" />
              Ticket Required
            </Label>
          </div>

          {data.ticket_required && (
            <div className="ml-7 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Status</Label>
                <Select
                  value={data.ticket_status ?? undefined}
                  onValueChange={(value) =>
                    updateField('ticket_status', value as TicketStatus)
                  }
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {TICKET_STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex items-center">
                          <StatusIndicator color={option.color} />
                          {option.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Purchase Date</Label>
                <DatePicker
                  value={data.ticket_purchase_date ?? ''}
                  onChange={(date) => updateField('ticket_purchase_date', date || null)}
                  placeholder="Select date"
                  disabled={disabled}
                />
              </div>
            </div>
          )}
        </div>

        {/* Time-off Section */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Checkbox
              id="timeoff_required"
              checked={data.timeoff_required ?? false}
              onCheckedChange={() =>
                toggleRequired('timeoff_required', 'timeoff_status', 'planned')
              }
              disabled={disabled}
            />
            <Label
              htmlFor="timeoff_required"
              className="flex items-center gap-2 cursor-pointer font-medium"
            >
              <Briefcase className="h-4 w-4" />
              Time Off Required
            </Label>
          </div>

          {data.timeoff_required && (
            <div className="ml-7 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Status</Label>
                <Select
                  value={data.timeoff_status ?? undefined}
                  onValueChange={(value) =>
                    updateField('timeoff_status', value as TimeoffStatus)
                  }
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIMEOFF_STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex items-center">
                          <StatusIndicator color={option.color} />
                          {option.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Booking Date</Label>
                <DatePicker
                  value={data.timeoff_booking_date ?? ''}
                  onChange={(date) => updateField('timeoff_booking_date', date || null)}
                  placeholder="Select date"
                  disabled={disabled}
                />
              </div>
            </div>
          )}
        </div>

        {/* Travel Section */}
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-center gap-3">
            <Checkbox
              id="travel_required"
              checked={data.travel_required ?? false}
              onCheckedChange={() =>
                toggleRequired('travel_required', 'travel_status', 'planned')
              }
              disabled={disabled}
            />
            <Label
              htmlFor="travel_required"
              className="flex items-center gap-2 cursor-pointer font-medium"
            >
              <Car className="h-4 w-4" />
              Travel Required
            </Label>
          </div>

          {data.travel_required && (
            <div className="ml-7 grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Status</Label>
                <Select
                  value={data.travel_status ?? undefined}
                  onValueChange={(value) =>
                    updateField('travel_status', value as TravelStatus)
                  }
                  disabled={disabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {TRAVEL_STATUS_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex items-center">
                          <StatusIndicator color={option.color} />
                          {option.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm text-muted-foreground">Booking Date</Label>
                <DatePicker
                  value={data.travel_booking_date ?? ''}
                  onChange={(date) => updateField('travel_booking_date', date || null)}
                  placeholder="Select date"
                  disabled={disabled}
                />
              </div>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

// ============================================================================
// Status Badge Component (for display in EventCard/EventDetails)
// ============================================================================

export interface LogisticsStatusBadgesProps {
  data: LogisticsData
  size?: 'sm' | 'md'
  className?: string
}

/**
 * Compact status badges for displaying logistics status on event cards.
 * Shows colored indicators for each required logistics item.
 */
export function LogisticsStatusBadges({
  data,
  size = 'sm',
  className,
}: LogisticsStatusBadgesProps) {
  const items: { label: string; color: 'red' | 'yellow' | 'green'; icon: React.ReactNode }[] = []

  if (data.ticket_required) {
    const statusOption = TICKET_STATUS_OPTIONS.find((o) => o.value === data.ticket_status)
    items.push({
      label: 'Ticket',
      color: statusOption?.color ?? 'red',
      icon: <Ticket className={cn('h-3 w-3', size === 'md' && 'h-4 w-4')} />,
    })
  }

  if (data.timeoff_required) {
    const statusOption = TIMEOFF_STATUS_OPTIONS.find((o) => o.value === data.timeoff_status)
    items.push({
      label: 'Time Off',
      color: statusOption?.color ?? 'red',
      icon: <Briefcase className={cn('h-3 w-3', size === 'md' && 'h-4 w-4')} />,
    })
  }

  if (data.travel_required) {
    const statusOption = TRAVEL_STATUS_OPTIONS.find((o) => o.value === data.travel_status)
    items.push({
      label: 'Travel',
      color: statusOption?.color ?? 'red',
      icon: <Car className={cn('h-3 w-3', size === 'md' && 'h-4 w-4')} />,
    })
  }

  if (items.length === 0) return null

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {items.map((item) => (
        <div
          key={item.label}
          className={cn(
            'flex items-center gap-1 rounded px-1.5 py-0.5',
            size === 'sm' && 'text-[10px]',
            size === 'md' && 'text-xs',
            item.color === 'red' && 'bg-red-500/10 text-red-500',
            item.color === 'yellow' && 'bg-yellow-500/10 text-yellow-500',
            item.color === 'green' && 'bg-green-500/10 text-green-500'
          )}
          title={`${item.label}: ${item.color === 'green' ? 'Complete' : item.color === 'yellow' ? 'In Progress' : 'Not Started'}`}
        >
          {item.icon}
        </div>
      ))}
    </div>
  )
}

export default LogisticsSection
