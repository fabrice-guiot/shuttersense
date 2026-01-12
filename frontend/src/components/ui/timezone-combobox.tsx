/**
 * Timezone Combobox Component
 *
 * Searchable combobox for selecting IANA timezones.
 * Groups timezones by region for easier navigation.
 */

import * as React from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

// ============================================================================
// Comprehensive IANA Timezone List
// ============================================================================

interface TimezoneOption {
  value: string
  label: string
  region: string
}

const TIMEZONES: TimezoneOption[] = [
  // No timezone option
  { value: '', label: 'No timezone (local)', region: 'None' },

  // North America
  { value: 'America/New_York', label: 'New York (Eastern)', region: 'North America' },
  { value: 'America/Chicago', label: 'Chicago (Central)', region: 'North America' },
  { value: 'America/Denver', label: 'Denver (Mountain)', region: 'North America' },
  { value: 'America/Phoenix', label: 'Phoenix (Arizona, no DST)', region: 'North America' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (Pacific)', region: 'North America' },
  { value: 'America/Anchorage', label: 'Anchorage (Alaska)', region: 'North America' },
  { value: 'Pacific/Honolulu', label: 'Honolulu (Hawaii)', region: 'North America' },
  { value: 'America/Toronto', label: 'Toronto', region: 'North America' },
  { value: 'America/Vancouver', label: 'Vancouver', region: 'North America' },
  { value: 'America/Montreal', label: 'Montreal', region: 'North America' },
  { value: 'America/Edmonton', label: 'Edmonton', region: 'North America' },
  { value: 'America/Winnipeg', label: 'Winnipeg', region: 'North America' },
  { value: 'America/Halifax', label: 'Halifax (Atlantic)', region: 'North America' },
  { value: 'America/St_Johns', label: "St. John's (Newfoundland)", region: 'North America' },
  { value: 'America/Mexico_City', label: 'Mexico City', region: 'North America' },
  { value: 'America/Tijuana', label: 'Tijuana', region: 'North America' },
  { value: 'America/Detroit', label: 'Detroit', region: 'North America' },
  { value: 'America/Indiana/Indianapolis', label: 'Indianapolis', region: 'North America' },
  { value: 'America/Boise', label: 'Boise', region: 'North America' },

  // Central & South America
  { value: 'America/Bogota', label: 'Bogota', region: 'South America' },
  { value: 'America/Lima', label: 'Lima', region: 'South America' },
  { value: 'America/Santiago', label: 'Santiago', region: 'South America' },
  { value: 'America/Sao_Paulo', label: 'Sao Paulo', region: 'South America' },
  { value: 'America/Buenos_Aires', label: 'Buenos Aires', region: 'South America' },
  { value: 'America/Caracas', label: 'Caracas', region: 'South America' },
  { value: 'America/Havana', label: 'Havana', region: 'Central America' },
  { value: 'America/Panama', label: 'Panama', region: 'Central America' },
  { value: 'America/Costa_Rica', label: 'Costa Rica', region: 'Central America' },
  { value: 'America/Guatemala', label: 'Guatemala', region: 'Central America' },

  // Europe
  { value: 'Europe/London', label: 'London', region: 'Europe' },
  { value: 'Europe/Dublin', label: 'Dublin', region: 'Europe' },
  { value: 'Europe/Lisbon', label: 'Lisbon', region: 'Europe' },
  { value: 'Europe/Paris', label: 'Paris', region: 'Europe' },
  { value: 'Europe/Berlin', label: 'Berlin', region: 'Europe' },
  { value: 'Europe/Amsterdam', label: 'Amsterdam', region: 'Europe' },
  { value: 'Europe/Brussels', label: 'Brussels', region: 'Europe' },
  { value: 'Europe/Rome', label: 'Rome', region: 'Europe' },
  { value: 'Europe/Madrid', label: 'Madrid', region: 'Europe' },
  { value: 'Europe/Barcelona', label: 'Barcelona', region: 'Europe' },
  { value: 'Europe/Zurich', label: 'Zurich', region: 'Europe' },
  { value: 'Europe/Vienna', label: 'Vienna', region: 'Europe' },
  { value: 'Europe/Stockholm', label: 'Stockholm', region: 'Europe' },
  { value: 'Europe/Oslo', label: 'Oslo', region: 'Europe' },
  { value: 'Europe/Copenhagen', label: 'Copenhagen', region: 'Europe' },
  { value: 'Europe/Helsinki', label: 'Helsinki', region: 'Europe' },
  { value: 'Europe/Warsaw', label: 'Warsaw', region: 'Europe' },
  { value: 'Europe/Prague', label: 'Prague', region: 'Europe' },
  { value: 'Europe/Budapest', label: 'Budapest', region: 'Europe' },
  { value: 'Europe/Athens', label: 'Athens', region: 'Europe' },
  { value: 'Europe/Bucharest', label: 'Bucharest', region: 'Europe' },
  { value: 'Europe/Sofia', label: 'Sofia', region: 'Europe' },
  { value: 'Europe/Istanbul', label: 'Istanbul', region: 'Europe' },
  { value: 'Europe/Moscow', label: 'Moscow', region: 'Europe' },
  { value: 'Europe/Kiev', label: 'Kyiv', region: 'Europe' },
  { value: 'Europe/Minsk', label: 'Minsk', region: 'Europe' },

  // Middle East
  { value: 'Asia/Jerusalem', label: 'Jerusalem', region: 'Middle East' },
  { value: 'Asia/Tel_Aviv', label: 'Tel Aviv', region: 'Middle East' },
  { value: 'Asia/Beirut', label: 'Beirut', region: 'Middle East' },
  { value: 'Asia/Dubai', label: 'Dubai', region: 'Middle East' },
  { value: 'Asia/Riyadh', label: 'Riyadh', region: 'Middle East' },
  { value: 'Asia/Kuwait', label: 'Kuwait', region: 'Middle East' },
  { value: 'Asia/Qatar', label: 'Qatar', region: 'Middle East' },
  { value: 'Asia/Bahrain', label: 'Bahrain', region: 'Middle East' },
  { value: 'Asia/Tehran', label: 'Tehran', region: 'Middle East' },
  { value: 'Asia/Baghdad', label: 'Baghdad', region: 'Middle East' },

  // Africa
  { value: 'Africa/Cairo', label: 'Cairo', region: 'Africa' },
  { value: 'Africa/Johannesburg', label: 'Johannesburg', region: 'Africa' },
  { value: 'Africa/Lagos', label: 'Lagos', region: 'Africa' },
  { value: 'Africa/Nairobi', label: 'Nairobi', region: 'Africa' },
  { value: 'Africa/Casablanca', label: 'Casablanca', region: 'Africa' },
  { value: 'Africa/Tunis', label: 'Tunis', region: 'Africa' },
  { value: 'Africa/Algiers', label: 'Algiers', region: 'Africa' },
  { value: 'Africa/Accra', label: 'Accra', region: 'Africa' },

  // South Asia
  { value: 'Asia/Kolkata', label: 'Mumbai / Delhi (India)', region: 'South Asia' },
  { value: 'Asia/Karachi', label: 'Karachi', region: 'South Asia' },
  { value: 'Asia/Dhaka', label: 'Dhaka', region: 'South Asia' },
  { value: 'Asia/Colombo', label: 'Colombo', region: 'South Asia' },
  { value: 'Asia/Kathmandu', label: 'Kathmandu', region: 'South Asia' },

  // Southeast Asia
  { value: 'Asia/Bangkok', label: 'Bangkok', region: 'Southeast Asia' },
  { value: 'Asia/Ho_Chi_Minh', label: 'Ho Chi Minh City', region: 'Southeast Asia' },
  { value: 'Asia/Singapore', label: 'Singapore', region: 'Southeast Asia' },
  { value: 'Asia/Kuala_Lumpur', label: 'Kuala Lumpur', region: 'Southeast Asia' },
  { value: 'Asia/Jakarta', label: 'Jakarta', region: 'Southeast Asia' },
  { value: 'Asia/Manila', label: 'Manila', region: 'Southeast Asia' },

  // East Asia
  { value: 'Asia/Tokyo', label: 'Tokyo', region: 'East Asia' },
  { value: 'Asia/Seoul', label: 'Seoul', region: 'East Asia' },
  { value: 'Asia/Shanghai', label: 'Shanghai / Beijing', region: 'East Asia' },
  { value: 'Asia/Hong_Kong', label: 'Hong Kong', region: 'East Asia' },
  { value: 'Asia/Taipei', label: 'Taipei', region: 'East Asia' },
  { value: 'Asia/Macau', label: 'Macau', region: 'East Asia' },

  // Central Asia
  { value: 'Asia/Almaty', label: 'Almaty', region: 'Central Asia' },
  { value: 'Asia/Tashkent', label: 'Tashkent', region: 'Central Asia' },
  { value: 'Asia/Yekaterinburg', label: 'Yekaterinburg', region: 'Central Asia' },
  { value: 'Asia/Novosibirsk', label: 'Novosibirsk', region: 'Central Asia' },
  { value: 'Asia/Vladivostok', label: 'Vladivostok', region: 'Central Asia' },

  // Australia & Pacific
  { value: 'Australia/Sydney', label: 'Sydney', region: 'Australia & Pacific' },
  { value: 'Australia/Melbourne', label: 'Melbourne', region: 'Australia & Pacific' },
  { value: 'Australia/Brisbane', label: 'Brisbane', region: 'Australia & Pacific' },
  { value: 'Australia/Perth', label: 'Perth', region: 'Australia & Pacific' },
  { value: 'Australia/Adelaide', label: 'Adelaide', region: 'Australia & Pacific' },
  { value: 'Australia/Darwin', label: 'Darwin', region: 'Australia & Pacific' },
  { value: 'Australia/Hobart', label: 'Hobart', region: 'Australia & Pacific' },
  { value: 'Pacific/Auckland', label: 'Auckland', region: 'Australia & Pacific' },
  { value: 'Pacific/Wellington', label: 'Wellington', region: 'Australia & Pacific' },
  { value: 'Pacific/Fiji', label: 'Fiji', region: 'Australia & Pacific' },
  { value: 'Pacific/Guam', label: 'Guam', region: 'Australia & Pacific' },
  { value: 'Pacific/Tahiti', label: 'Tahiti', region: 'Australia & Pacific' },

  // UTC
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)', region: 'UTC' },
]

// Group timezones by region
const TIMEZONE_GROUPS = TIMEZONES.reduce((groups, tz) => {
  if (!groups[tz.region]) {
    groups[tz.region] = []
  }
  groups[tz.region].push(tz)
  return groups
}, {} as Record<string, TimezoneOption[]>)

// Order of regions for display
const REGION_ORDER = [
  'None',
  'North America',
  'Central America',
  'South America',
  'Europe',
  'Middle East',
  'Africa',
  'South Asia',
  'Southeast Asia',
  'East Asia',
  'Central Asia',
  'Australia & Pacific',
  'UTC',
]

// ============================================================================
// Component
// ============================================================================

interface TimezoneComboboxProps {
  value?: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function TimezoneCombobox({
  value,
  onChange,
  placeholder = 'Select timezone...',
  disabled = false,
  className,
}: TimezoneComboboxProps) {
  const [open, setOpen] = React.useState(false)

  // Find the selected timezone for display
  const selectedTimezone = TIMEZONES.find((tz) => tz.value === value)

  // Get current timezone abbreviation for display
  const getTimezoneAbbr = (ianaTimezone: string): string => {
    if (!ianaTimezone) return ''
    try {
      const formatter = new Intl.DateTimeFormat('en-US', {
        timeZone: ianaTimezone,
        timeZoneName: 'short',
      })
      const parts = formatter.formatToParts(new Date())
      const tzPart = parts.find((part) => part.type === 'timeZoneName')
      return tzPart?.value || ''
    } catch {
      return ''
    }
  }

  const displayValue = selectedTimezone
    ? `${selectedTimezone.label}${selectedTimezone.value ? ` (${getTimezoneAbbr(selectedTimezone.value)})` : ''}`
    : placeholder

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            'w-full justify-between font-normal',
            !value && 'text-muted-foreground',
            className
          )}
        >
          <span className="truncate">{displayValue}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search timezones..." />
          <CommandList className="max-h-[300px]">
            <CommandEmpty>No timezone found.</CommandEmpty>
            {REGION_ORDER.map((region) => {
              const timezones = TIMEZONE_GROUPS[region]
              if (!timezones) return null
              return (
                <CommandGroup key={region} heading={region === 'None' ? '' : region}>
                  {timezones.map((tz) => (
                    <CommandItem
                      key={tz.value || 'none'}
                      value={`${tz.label} ${tz.region}`}
                      onSelect={() => {
                        onChange(tz.value)
                        setOpen(false)
                      }}
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4',
                          value === tz.value ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      <span className="flex-1">{tz.label}</span>
                      {tz.value && (
                        <span className="text-muted-foreground text-xs ml-2">
                          {getTimezoneAbbr(tz.value)}
                        </span>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              )
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

export default TimezoneCombobox
