/**
 * DateRangeFilter Component
 *
 * Filter component for selecting date ranges in trend views
 */

import { useState, useEffect } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
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
  { value: 'last_year', label: 'Last year' },
  { value: 'all_time', label: 'All time' }
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
  const handleFromDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onDateChange(e.target.value, toDate)
  }

  const handleToDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onDateChange(fromDate, e.target.value)
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <Label htmlFor="date-preset" className="text-sm font-medium">
            Date Range
          </Label>
          <Select value={preset} onValueChange={handlePresetChange}>
            <SelectTrigger id="date-preset" className="mt-1">
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
        </div>

        {showCustom && (
          <>
            <div className="flex-1">
              <Label htmlFor="from-date" className="text-sm font-medium">
                From
              </Label>
              <Input
                id="from-date"
                type="date"
                value={fromDate}
                onChange={handleFromDateChange}
                className="mt-1"
              />
            </div>
            <div className="flex-1">
              <Label htmlFor="to-date" className="text-sm font-medium">
                To
              </Label>
              <Input
                id="to-date"
                type="date"
                value={toDate}
                onChange={handleToDateChange}
                className="mt-1"
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
