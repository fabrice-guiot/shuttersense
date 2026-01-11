/**
 * Date Picker Component
 *
 * A date input with a calendar popover for selecting dates.
 * Combines Calendar and Popover components.
 */

import * as React from 'react'
import { format, parse } from 'date-fns'
import { Calendar as CalendarIcon } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface DatePickerProps {
  /** Selected date as ISO string (YYYY-MM-DD) or undefined */
  value?: string
  /** Callback when date changes, receives ISO string (YYYY-MM-DD) */
  onChange?: (date: string | undefined) => void
  /** Placeholder text when no date selected */
  placeholder?: string
  /** Additional class names */
  className?: string
  /** Whether the picker is disabled */
  disabled?: boolean
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Pick a date',
  className,
  disabled = false,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false)

  // Convert ISO string to Date object for the calendar
  const selectedDate = value
    ? parse(value, 'yyyy-MM-dd', new Date())
    : undefined

  // Handle date selection
  const handleSelect = (date: Date | undefined) => {
    if (date) {
      // Format as ISO date string (YYYY-MM-DD)
      const isoDate = format(date, 'yyyy-MM-dd')
      onChange?.(isoDate)
    } else {
      onChange?.(undefined)
    }
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-left font-normal',
            !value && 'text-muted-foreground',
            className
          )}
          disabled={disabled}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? (
            format(selectedDate!, 'PPP')
          ) : (
            <span>{placeholder}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={handleSelect}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}
