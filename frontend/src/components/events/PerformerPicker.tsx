/**
 * Performer Picker Component
 *
 * Searchable picker for selecting event performers.
 * Shows performers filtered by category matching.
 *
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import * as React from 'react'
import { useState } from 'react'
import { Check, ChevronsUpDown, Users, X, Instagram } from 'lucide-react'
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
import { usePerformersByCategory } from '@/hooks/usePerformers'
import type { Performer } from '@/contracts/api/performer-api'

// ============================================================================
// Types
// ============================================================================

export interface PerformerPickerProps {
  /** Category GUID to filter performers (required for category matching) */
  categoryGuid: string | null
  /** Currently selected performer */
  value: Performer | null
  /** Called when performer is selected */
  onChange: (performer: Performer | null) => void
  /** Placeholder text */
  placeholder?: string
  /** Disable the picker */
  disabled?: boolean
  /** Additional CSS classes */
  className?: string
  /** Performers already added to exclude from selection */
  excludeGuids?: string[]
}

// ============================================================================
// Component
// ============================================================================

export function PerformerPicker({
  categoryGuid,
  value,
  onChange,
  placeholder = 'Select performer...',
  disabled = false,
  className,
  excludeGuids = [],
}: PerformerPickerProps) {
  const [open, setOpen] = useState(false)

  // Fetch performers for the category
  const { performers, loading: loadingPerformers } = usePerformersByCategory(categoryGuid)

  // Filter out excluded performers
  const availablePerformers = performers.filter(p => !excludeGuids.includes(p.guid))

  // Format performer display text
  const getDisplayText = (performer: Performer | null): string => {
    if (!performer) return placeholder
    return performer.name
  }

  // Handle selecting a performer
  const handleSelectPerformer = (performer: Performer) => {
    onChange(performer)
    setOpen(false)
  }

  // Clear selection
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(null)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled || !categoryGuid}
          className={cn(
            'w-full justify-between font-normal',
            !value && 'text-muted-foreground',
            className
          )}
        >
          <span className="flex items-center gap-2 truncate">
            <Users className="h-4 w-4 shrink-0 opacity-50" />
            <span className="truncate">{getDisplayText(value)}</span>
          </span>
          <div className="flex items-center gap-1">
            {value && (
              <X
                className="h-4 w-4 shrink-0 opacity-50 hover:opacity-100"
                onClick={handleClear}
              />
            )}
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[350px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search performers..." />
          <CommandList className="max-h-[300px]">
            {loadingPerformers ? (
              <div className="flex items-center justify-center py-6">
                <span className="text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : (
              <>
                <CommandEmpty>
                  {categoryGuid
                    ? 'No performers found for this category.'
                    : 'Select a category first.'}
                </CommandEmpty>
                {availablePerformers.length > 0 && (
                  <CommandGroup heading="Performers">
                    {availablePerformers.map((performer) => (
                      <CommandItem
                        key={performer.guid}
                        value={performer.name}
                        onSelect={() => handleSelectPerformer(performer)}
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            value?.guid === performer.guid ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        <div className="flex flex-col flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium">{performer.name}</span>
                          </div>
                          {performer.instagram_handle && (
                            <div className="flex items-center gap-1 mt-0.5 text-xs text-muted-foreground">
                              <Instagram className="h-3 w-3" />
                              <span>@{performer.instagram_handle}</span>
                            </div>
                          )}
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                )}
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

export default PerformerPicker
