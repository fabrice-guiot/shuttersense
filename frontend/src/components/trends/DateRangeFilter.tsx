/**
 * DateRangeFilter Component
 *
 * Filter component for selecting date ranges in trend views
 */

import { useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { DatePicker } from '@/components/ui/date-picker'
import type { DateRangePreset } from '@/contracts/api/trends-api'
import { getDateRangeFromPreset } from '@/contracts/api/trends-api'

interface DateRangeFilterProps {
  fromDate: string
  toDate: string
  onDateChange: (from: string, to: string) => void
  className?: string
}

const DATE_RANGE_PRESETS: Array<{ value: DateRangePreset; label: string }> = [
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
  { value: 'last_year', label: 'Last year' }
]

export function DateRangeFilter({
  fromDate,
  toDate,
  onDateChange,
  className = ''
}: DateRangeFilterProps) {
  const [preset, setPreset] = useState<DateRangePreset | 'custom'>('last_30_days')
  const [showCustom, setShowCustom] = useState(false)

  // Handle preset selection
  const handlePresetChange = (value: string) => {
    if (value === 'custom') {
      setPreset('custom')
      setShowCustom(true)
    } else {
      setPreset(value as DateRangePreset)
      setShowCustom(false)
      const { from_date, to_date } = getDateRangeFromPreset(value as DateRangePreset)
      onDateChange(from_date, to_date)
    }
  }

  // Handle custom date changes
  const handleFromDateChange = (date: string | undefined) => {
    onDateChange(date || '', toDate)
  }

  const handleToDateChange = (date: string | undefined) => {
    onDateChange(fromDate, date || '')
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <Label className="text-sm font-medium">Date Range</Label>
      <Select value={preset} onValueChange={handlePresetChange}>
        <SelectTrigger>
          <SelectValue placeholder="Select date range" />
        </SelectTrigger>
        <SelectContent>
          {DATE_RANGE_PRESETS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
          <SelectItem value="custom">Custom range</SelectItem>
        </SelectContent>
      </Select>

      {showCustom && (
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">From</Label>
            <DatePicker
              value={fromDate}
              onChange={handleFromDateChange}
              placeholder="Start date"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">To</Label>
            <DatePicker
              value={toDate}
              onChange={handleToDateChange}
              placeholder="End date"
            />
          </div>
        </div>
      )}
    </div>
  )
}
