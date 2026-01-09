import { Search, X } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import type { FiltersSectionProps } from '@/contracts/components/collection-components'
import type { CollectionType } from '@/contracts/api/collection-api'
import {
  COLLECTION_STATE_FILTER_OPTIONS,
  COLLECTION_TYPE_FILTER_OPTIONS
} from '@/contracts/components/collection-components'
import { cn } from '@/lib/utils'

// Collection types still in beta/QA - remove from this set once QA'd
const BETA_COLLECTION_TYPES: Set<CollectionType> = new Set(['gcs', 'smb'])

function isBetaCollectionType(type: CollectionType): boolean {
  return BETA_COLLECTION_TYPES.has(type)
}

// Beta chip component for consistent styling
function BetaChip() {
  return (
    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
      Beta
    </span>
  )
}

// Max length for search input (T031)
const SEARCH_MAX_LENGTH = 100

/**
 * Filters section for collection list
 * Provides search, state, type, and accessibility filtering
 */
export function FiltersSection({
  selectedState,
  setSelectedState,
  selectedType,
  setSelectedType,
  accessibleOnly,
  setAccessibleOnly,
  search = '',
  onSearchChange,
  className
}: FiltersSectionProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-lg border border-border bg-card p-4',
        className
      )}
    >
      {/* Search Input (Issue #38) */}
      {onSearchChange && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="search-input" className="text-sm font-medium">
            Search
          </Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="search-input"
              type="text"
              placeholder="Search by collection name..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              maxLength={SEARCH_MAX_LENGTH}
              className="pl-9 pr-9"
            />
            {search && (
              <Button
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0"
                onClick={() => onSearchChange('')}
                aria-label="Clear search"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Filter Row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
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
                  {option.value !== 'ALL' && isBetaCollectionType(option.value as CollectionType) ? (
                    <span className="flex items-center gap-2">
                      {option.label}
                      <BetaChip />
                    </span>
                  ) : (
                    option.label
                  )}
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
    </div>
  )
}
