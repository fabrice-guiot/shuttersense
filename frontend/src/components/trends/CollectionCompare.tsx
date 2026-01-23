/**
 * CollectionCompare Component
 *
 * Search-based multi-select for choosing collections to compare in trend views.
 * Designed to handle 1000+ collections efficiently with search filtering.
 */

import { useState, useMemo } from 'react'
import { Check, X, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList
} from '@/components/ui/command'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface Collection {
  id: number
  name: string
}

interface CollectionCompareProps {
  collections: Collection[]
  selectedIds: number[]
  onSelectionChange: (ids: number[]) => void
  maxSelections?: number
  className?: string
}

export function CollectionCompare({
  collections,
  selectedIds,
  onSelectionChange,
  maxSelections = 5,
  className = ''
}: CollectionCompareProps) {
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Get selected collection objects
  const selectedCollections = useMemo(() => {
    return collections.filter((c) => selectedIds.includes(c.id))
  }, [collections, selectedIds])

  // Filter collections based on search query (case-insensitive)
  const filteredCollections = useMemo(() => {
    if (!searchQuery.trim()) {
      // Show first 50 when no search query (for initial display)
      return collections.slice(0, 50)
    }
    const query = searchQuery.toLowerCase()
    return collections
      .filter((c) => c.name.toLowerCase().includes(query))
      .slice(0, 50) // Limit results to prevent performance issues
  }, [collections, searchQuery])

  // Handle selecting a collection
  const handleSelect = (collectionId: number) => {
    const isSelected = selectedIds.includes(collectionId)

    if (isSelected) {
      // Remove from selection
      onSelectionChange(selectedIds.filter((id) => id !== collectionId))
    } else {
      // Add to selection (if under limit)
      if (selectedIds.length < maxSelections) {
        onSelectionChange([...selectedIds, collectionId])
      }
    }
  }

  // Handle removing a selected collection
  const handleRemove = (collectionId: number) => {
    onSelectionChange(selectedIds.filter((id) => id !== collectionId))
  }

  // Handle clear all
  const handleClearAll = () => {
    onSelectionChange([])
  }

  const isAtLimit = selectedIds.length >= maxSelections

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Compare Collections</Label>
        {selectedIds.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="h-auto py-1 px-2 text-xs"
          >
            Clear all
          </Button>
        )}
      </div>

      {/* Search trigger */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal"
            disabled={isAtLimit}
          >
            <span className="text-muted-foreground">
              {isAtLimit
                ? `Maximum ${maxSelections} selected`
                : 'Search collections...'}
            </span>
            <Search className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Type to search collections..."
              value={searchQuery}
              onValueChange={setSearchQuery}
            />
            <CommandList>
              <CommandEmpty>
                {searchQuery
                  ? 'No collections found.'
                  : 'Start typing to search...'}
              </CommandEmpty>
              <CommandGroup>
                {filteredCollections.map((collection) => {
                  const isSelected = selectedIds.includes(collection.id)
                  const isDisabled = !isSelected && isAtLimit

                  return (
                    <CommandItem
                      key={collection.id}
                      value={collection.id.toString()}
                      onSelect={() => handleSelect(collection.id)}
                      disabled={isDisabled}
                      className={cn(isDisabled && 'opacity-50')}
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4',
                          isSelected ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      <span className="truncate">{collection.name}</span>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
              {filteredCollections.length >= 50 && (
                <div className="px-2 py-2 text-xs text-muted-foreground text-center border-t">
                  Showing first 50 results. Type to refine search.
                </div>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Selected collections as badges */}
      {selectedCollections.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedCollections.map((collection) => (
            <Badge key={collection.id} variant="secondary" className="pr-1 text-xs">
              <span className="truncate max-w-[150px]">{collection.name}</span>
              <button
                onClick={() => handleRemove(collection.id)}
                className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
                aria-label={`Remove ${collection.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Helper text */}
      {selectedIds.length === 0 && (
        <p className="text-xs text-muted-foreground">
          All collections included. Select up to {maxSelections} to compare specific ones.
        </p>
      )}
    </div>
  )
}
