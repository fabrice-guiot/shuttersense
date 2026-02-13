/**
 * DateRangePicker Component
 *
 * Dropdown with grouped presets (Rolling / Monthly) and a custom date range
 * mode. Designed for compact inline use above event list views.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 7, US5)
 */

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { DatePicker } from '@/components/ui/date-picker'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import {
  PRESET_LABELS,
  PRESET_GROUPS,
  type RangePreset,
  type DateRange,
} from '@/hooks/useDateRange'

// ============================================================================
// Types
// ============================================================================

interface DateRangePickerProps {
  preset: RangePreset
  range: DateRange
  customStart: string
  customEnd: string
  onPresetChange: (preset: RangePreset) => void
  onCustomRangeChange: (start: string, end: string) => void
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function DateRangePicker({
  preset,
  range,
  customStart,
  customEnd,
  onPresetChange,
  onCustomRangeChange,
  className,
}: DateRangePickerProps) {
  const isCustom = preset === 'custom'

  return (
    <div className={cn('flex flex-col gap-2 sm:flex-row sm:items-end', className)}>
      <div className="w-full sm:w-48">
        <Label className="text-xs text-muted-foreground mb-1 block">Date Range</Label>
        <Select value={preset} onValueChange={(v) => onPresetChange(v as RangePreset)}>
          <SelectTrigger className="h-8 text-sm">
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            {PRESET_GROUPS.map((group, gi) => (
              <SelectGroup key={group.label}>
                {gi > 0 && <SelectSeparator />}
                <SelectLabel>{group.label}</SelectLabel>
                {group.presets.map(p => (
                  <SelectItem key={p} value={p}>
                    {PRESET_LABELS[p]}
                  </SelectItem>
                ))}
              </SelectGroup>
            ))}
            <SelectSeparator />
            <SelectItem value="custom">{PRESET_LABELS.custom}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isCustom ? (
        <div className="flex items-end gap-2">
          <div>
            <Label className="text-xs text-muted-foreground mb-1 block">From</Label>
            <DatePicker
              value={customStart || undefined}
              onChange={v => onCustomRangeChange(v ?? '', customEnd)}
              placeholder="Start date"
              className="h-8 text-sm w-40"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground mb-1 block">To</Label>
            <DatePicker
              value={customEnd || undefined}
              onChange={v => onCustomRangeChange(customStart, v ?? '')}
              placeholder="End date"
              className="h-8 text-sm w-40"
            />
          </div>
        </div>
      ) : (
        <span className="text-xs text-muted-foreground pb-1">
          {range.startDate} — {range.endDate}
        </span>
      )}
    </div>
  )
}
