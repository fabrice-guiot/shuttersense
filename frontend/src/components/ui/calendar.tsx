/**
 * Calendar Component
 *
 * A date picker calendar based on react-day-picker v9.
 * Styled to match shadcn/ui design system.
 */

import * as React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { DayPicker, DayFlag, SelectionState, UI } from 'react-day-picker'

import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button'

export type CalendarProps = React.ComponentProps<typeof DayPicker>

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn('p-3', className)}
      classNames={{
        [UI.Months]: 'relative flex flex-col sm:flex-row gap-4',
        [UI.Month]: 'space-y-4',
        [UI.MonthCaption]: 'flex justify-center pt-1 relative items-center h-7',
        [UI.CaptionLabel]: 'text-sm font-medium',
        [UI.Nav]: 'flex items-center gap-1',
        [UI.PreviousMonthButton]: cn(
          buttonVariants({ variant: 'outline' }),
          'absolute left-1 top-0 h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100'
        ),
        [UI.NextMonthButton]: cn(
          buttonVariants({ variant: 'outline' }),
          'absolute right-1 top-0 h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100'
        ),
        [UI.MonthGrid]: 'w-full border-collapse',
        [UI.Weekdays]: 'flex',
        [UI.Weekday]: 'text-muted-foreground rounded-md w-9 font-normal text-[0.8rem] text-center',
        [UI.Week]: 'flex w-full mt-2',
        [UI.Day]: cn(
          'h-9 w-9 text-center text-sm p-0 relative',
          '[&:has([aria-selected].day-range-end)]:rounded-r-md',
          '[&:has([aria-selected].day-outside)]:bg-accent/50',
          '[&:has([aria-selected])]:bg-accent',
          'first:[&:has([aria-selected])]:rounded-l-md',
          'last:[&:has([aria-selected])]:rounded-r-md',
          'focus-within:relative focus-within:z-20'
        ),
        [UI.DayButton]: cn(
          buttonVariants({ variant: 'ghost' }),
          'h-9 w-9 p-0 font-normal aria-selected:opacity-100'
        ),
        [SelectionState.range_end]: 'day-range-end',
        [SelectionState.selected]:
          'bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground',
        [SelectionState.range_middle]:
          'aria-selected:bg-accent aria-selected:text-accent-foreground',
        [DayFlag.today]: 'bg-accent text-accent-foreground',
        [DayFlag.outside]:
          'day-outside text-muted-foreground opacity-50 aria-selected:bg-accent/50 aria-selected:text-muted-foreground',
        [DayFlag.disabled]: 'text-muted-foreground opacity-50',
        [DayFlag.hidden]: 'invisible',
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) =>
          orientation === 'left' ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          ),
      }}
      {...props}
    />
  )
}
Calendar.displayName = 'Calendar'

export { Calendar }
