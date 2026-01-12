/**
 * Organizer Picker Component
 *
 * Searchable picker for selecting event organizers.
 * Shows organizers filtered by category matching.
 *
 * Issue #39 - Calendar Events feature (Phase 9)
 */

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Check, ChevronsUpDown, Building2, Star, X } from 'lucide-react'
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
import { useOrganizersByCategory } from '@/hooks/useOrganizers'
import type { Organizer } from '@/contracts/api/organizer-api'

// ============================================================================
// Rating Display (inline)
// ============================================================================

function RatingDisplay({ rating }: { rating: number | null }) {
  if (rating === null) return null

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            'h-2.5 w-2.5',
            i < rating
              ? 'fill-yellow-400 text-yellow-400'
              : 'text-muted-foreground/30'
          )}
        />
      ))}
    </div>
  )
}

// ============================================================================
// Types
// ============================================================================

export interface OrganizerPickerProps {
  /** Category GUID to filter organizers (required for category matching) */
  categoryGuid: string | null
  /** Currently selected organizer */
  value: Organizer | null
  /** Called when organizer is selected */
  onChange: (organizer: Organizer | null) => void
  /** Called when an organizer with ticket_required_default is selected */
  onTicketRequiredHint?: (ticketRequired: boolean) => void
  /** Placeholder text */
  placeholder?: string
  /** Disable the picker */
  disabled?: boolean
  /** Additional CSS classes */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function OrganizerPicker({
  categoryGuid,
  value,
  onChange,
  onTicketRequiredHint,
  placeholder = 'Select organizer...',
  disabled = false,
  className,
}: OrganizerPickerProps) {
  const [open, setOpen] = useState(false)

  // Fetch organizers for the category
  const { organizers, loading: loadingOrganizers } = useOrganizersByCategory(categoryGuid)

  // Format organizer display text
  const getDisplayText = (organizer: Organizer | null): string => {
    if (!organizer) return placeholder
    return organizer.name
  }

  // Handle selecting an organizer
  const handleSelectOrganizer = (organizer: Organizer) => {
    onChange(organizer)
    if (organizer.ticket_required_default && onTicketRequiredHint) {
      onTicketRequiredHint(true)
    }
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
            <Building2 className="h-4 w-4 shrink-0 opacity-50" />
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
          <CommandInput placeholder="Search organizers..." />
          <CommandList className="max-h-[300px]">
            {loadingOrganizers ? (
              <div className="flex items-center justify-center py-6">
                <span className="text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : (
              <>
                <CommandEmpty>
                  {categoryGuid
                    ? 'No organizers found for this category.'
                    : 'Select a category first.'}
                </CommandEmpty>
                {organizers.length > 0 && (
                  <CommandGroup heading="Organizers">
                    {organizers.map((organizer) => (
                      <CommandItem
                        key={organizer.guid}
                        value={organizer.name}
                        onSelect={() => handleSelectOrganizer(organizer)}
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            value?.guid === organizer.guid ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        <div className="flex flex-col flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium">{organizer.name}</span>
                            {organizer.ticket_required_default && (
                              <span className="text-[10px] px-1 py-0.5 rounded bg-primary/10 text-primary">
                                Ticket
                              </span>
                            )}
                          </div>
                          {organizer.rating !== null && (
                            <div className="mt-0.5">
                              <RatingDisplay rating={organizer.rating} />
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

export default OrganizerPicker
