import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import type { FiltersSectionProps } from '@/contracts/components/collection-components'
import {
  COLLECTION_STATE_FILTER_OPTIONS,
  COLLECTION_TYPE_FILTER_OPTIONS
} from '@/contracts/components/collection-components'
import { cn } from '@/lib/utils'

/**
 * Filters section for collection list
 * Provides state, type, and accessibility filtering
 */
export function FiltersSection({
  selectedState,
  setSelectedState,
  selectedType,
  setSelectedType,
  accessibleOnly,
  setAccessibleOnly,
  className
}: FiltersSectionProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-end',
        className
      )}
    >
      {/* State Filter */}
      <div className="flex flex-col gap-2 flex-1">
        <Label htmlFor="state-filter" className="text-sm font-medium">
          State
        </Label>
        <Select
          value={selectedState}
          onValueChange={setSelectedState}
        >
          <SelectTrigger id="state-filter" className="w-full">
            <SelectValue placeholder="All States" />
          </SelectTrigger>
          <SelectContent>
            {COLLECTION_STATE_FILTER_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Type Filter */}
      <div className="flex flex-col gap-2 flex-1">
        <Label htmlFor="type-filter" className="text-sm font-medium">
          Type
        </Label>
        <Select
          value={selectedType}
          onValueChange={setSelectedType}
        >
          <SelectTrigger id="type-filter" className="w-full">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            {COLLECTION_TYPE_FILTER_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Accessible Only Filter */}
      <div className="flex items-center gap-2 flex-1">
        <Checkbox
          id="accessible-only"
          checked={accessibleOnly}
          onCheckedChange={setAccessibleOnly}
        />
        <Label
          htmlFor="accessible-only"
          className="text-sm font-medium cursor-pointer"
        >
          Accessible Only
        </Label>
      </div>
    </div>
  )
}
