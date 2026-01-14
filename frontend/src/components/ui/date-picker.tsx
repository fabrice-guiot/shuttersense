/**
 * Date Picker Component
 *
 * A date input with a calendar popover for selecting dates.
 * Combines Calendar and Popover components.
 */

import * as React from 'react'
import { format, parse } from 'date-fns'
import { Calendar as CalendarIcon, X } from 'lucide-react'

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
  /** Whether the date can be cleared (shows X button when value is set) */
  clearable?: boolean
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Pick a date',
  className,
  disabled = false,
  clearable = false,
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

  // Handle clear button click
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent popover from opening
    onChange?.(undefined)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-left font-normal relative',
            !value && 'text-muted-foreground',
            clearable && value && 'pr-8', // Make room for clear button
            className
          )}
          disabled={disabled}
        >
          <CalendarIcon className="mr-2 h-4 w-4 shrink-0" />
          <span className="flex-1 truncate">
            {value ? format(selectedDate!, 'PPP') : placeholder}
          </span>
          {clearable && value && !disabled && (
            <span
              role="button"
              tabIndex={0}
              onClick={handleClear}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  handleClear(e as unknown as React.MouseEvent)
                }
              }}
              className="absolute right-2 p-0.5 rounded-sm hover:bg-muted"
              aria-label="Clear date"
            >
              <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start" side="bottom">
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={handleSelect}
          defaultMonth={selectedDate}
          fixedWeeks
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}
