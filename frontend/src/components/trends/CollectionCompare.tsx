/**
 * CollectionCompare Component
 *
 * Multi-select for choosing collections to compare in trend views
 */

import { useState, useMemo } from 'react'
import { Check, ChevronsUpDown, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
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
  // Get selected collection objects
  const selectedCollections = useMemo(() => {
    return collections.filter((c) => selectedIds.includes(c.id))
  }, [collections, selectedIds])

  // Handle checkbox toggle
  const handleToggle = (collectionId: number) => {
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

  // Handle select all
  const handleSelectAll = () => {
    const idsToSelect = collections.slice(0, maxSelections).map((c) => c.id)
    onSelectionChange(idsToSelect)
  }

  // Handle clear all
  const handleClearAll = () => {
    onSelectionChange([])
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">Compare Collections</Label>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={handleSelectAll} disabled={collections.length === 0}>
            Select All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            disabled={selectedIds.length === 0}
          >
            Clear
          </Button>
        </div>
      </div>

      {/* Selected collections as badges */}
      {selectedCollections.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedCollections.map((collection) => (
            <Badge key={collection.id} variant="secondary" className="pr-1">
              {collection.name}
              <button
                onClick={() => handleRemove(collection.id)}
                className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Collection list with checkboxes */}
      <div className="border rounded-md max-h-48 overflow-y-auto">
        {collections.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">No collections available</div>
        ) : (
          <div className="p-2 space-y-1">
            {collections.map((collection) => {
              const isSelected = selectedIds.includes(collection.id)
              const isDisabled = !isSelected && selectedIds.length >= maxSelections

              return (
                <label
                  key={collection.id}
                  className={cn(
                    'flex items-center gap-2 p-2 rounded-md cursor-pointer hover:bg-muted',
                    isSelected && 'bg-muted',
                    isDisabled && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  <Checkbox
                    checked={isSelected}
                    disabled={isDisabled}
                    onCheckedChange={() => handleToggle(collection.id)}
                  />
                  <span className="text-sm">{collection.name}</span>
                </label>
              )
            })}
          </div>
        )}
      </div>

      {selectedIds.length >= maxSelections && (
        <p className="text-xs text-muted-foreground">
          Maximum {maxSelections} collections can be compared
        </p>
      )}
    </div>
  )
}
