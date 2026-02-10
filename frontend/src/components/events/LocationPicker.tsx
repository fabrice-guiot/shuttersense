/**
 * Location Picker Component
 *
 * Searchable picker for selecting or creating event locations.
 * Supports:
 * - Selecting from known locations (filtered by category)
 * - Entering a new address with geocoding
 * - Auto-creating one-time locations (is_known=false)
 * - Optionally saving as known location
 *
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Check, ChevronsUpDown, MapPin, Search, Loader2, Plus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { useLocationsByCategory } from '@/hooks/useLocations'
import * as locationService from '@/services/locations'
import type { Location, GeocodeResponse, LocationCreateRequest } from '@/contracts/api/location-api'

// ============================================================================
// Types
// ============================================================================

/** Logistics hints from location defaults */
export interface LocationLogisticsHint {
  timeoff_required?: boolean
  travel_required?: boolean
}

export interface LocationPickerProps {
  /** Category GUID to filter known locations (required for category matching) */
  categoryGuid: string | null
  /** Currently selected location */
  value: Location | null
  /** Called when location is selected/created */
  onChange: (location: Location | null) => void
  /** Called when a location with timezone is selected (for timezone suggestion) */
  onTimezoneHint?: (timezone: string) => void
  /** Called when a location with logistics defaults is selected */
  onLogisticsHint?: (hint: LocationLogisticsHint) => void
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

export function LocationPicker({
  categoryGuid,
  value,
  onChange,
  onTimezoneHint,
  onLogisticsHint,
  placeholder = 'Select or enter location...',
  disabled = false,
  className,
}: LocationPickerProps) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<'select' | 'new'>('select')
  const [addressInput, setAddressInput] = useState('')
  const [isGeocoding, setIsGeocoding] = useState(false)
  const [geocodeResult, setGeocodeResult] = useState<GeocodeResponse | null>(null)
  const [saveAsKnown, setSaveAsKnown] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [geocodeError, setGeocodeError] = useState<string | null>(null)

  // Fetch known locations for the category
  const { locations: knownLocations, loading: loadingLocations } = useLocationsByCategory(
    categoryGuid,
    true // known_only
  )

  // Reset state when popover closes
  useEffect(() => {
    if (!open) {
      setMode('select')
      setAddressInput('')
      setGeocodeResult(null)
      setSaveAsKnown(false)
      setGeocodeError(null)
    }
  }, [open])

  // Format location display text
  const getDisplayText = (location: Location | null): string => {
    if (!location) return placeholder
    const parts = [location.name]
    if (location.city) parts.push(location.city)
    if (location.country && location.country !== location.city) parts.push(location.country)
    return parts.join(', ')
  }

  // Handle selecting a known location
  const handleSelectLocation = (location: Location) => {
    onChange(location)
    if (location.timezone && onTimezoneHint) {
      onTimezoneHint(location.timezone)
    }
    // Suggest logistics defaults if available (use nullish checks to preserve explicit false)
    if (onLogisticsHint && (location.timeoff_required_default != null || location.travel_required_default != null)) {
      onLogisticsHint({
        timeoff_required: location.timeoff_required_default ?? undefined,
        travel_required: location.travel_required_default ?? undefined,
      })
    }
    setOpen(false)
  }

  // Handle geocoding an address
  const handleGeocode = async () => {
    if (!addressInput.trim()) return

    setIsGeocoding(true)
    setGeocodeError(null)
    setGeocodeResult(null)

    try {
      const result = await locationService.geocodeAddress(addressInput.trim())
      if (result) {
        setGeocodeResult(result)
      } else {
        setGeocodeError('Address not found. Please try a different address.')
      }
    } catch (err) {
      setGeocodeError('Failed to lookup address. Please try again.')
    } finally {
      setIsGeocoding(false)
    }
  }

  // Handle Enter key in address input
  const handleAddressKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      e.stopPropagation()
      handleGeocode()
    }
  }

  // Create location from geocode result
  const handleCreateLocation = async () => {
    if (!geocodeResult || !categoryGuid) return

    setIsCreating(true)
    try {
      // Build location name from address components
      const nameParts = []
      if (geocodeResult.address) nameParts.push(geocodeResult.address)
      if (geocodeResult.city) nameParts.push(geocodeResult.city)
      const locationName = nameParts.length > 0 ? nameParts.join(', ') : addressInput

      const createData: LocationCreateRequest = {
        name: locationName,
        category_guid: categoryGuid,
        address: geocodeResult.address,
        city: geocodeResult.city,
        state: geocodeResult.state,
        country: geocodeResult.country,
        postal_code: geocodeResult.postal_code,
        latitude: geocodeResult.latitude,
        longitude: geocodeResult.longitude,
        timezone: geocodeResult.timezone,
        is_known: saveAsKnown,
      }

      const newLocation = await locationService.createLocation(createData)
      onChange(newLocation)
      if (newLocation.timezone && onTimezoneHint) {
        onTimezoneHint(newLocation.timezone)
      }
      // Suggest logistics defaults if available (use nullish checks to preserve explicit false)
      if (onLogisticsHint && (newLocation.timeoff_required_default != null || newLocation.travel_required_default != null)) {
        onLogisticsHint({
          timeoff_required: newLocation.timeoff_required_default ?? undefined,
          travel_required: newLocation.travel_required_default ?? undefined,
        })
      }
      setOpen(false)
    } catch (err) {
      setGeocodeError('Failed to create location. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  // Clear selection
  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange(null)
  }

  // Format geocode result for display
  const formatGeocodeResult = (result: GeocodeResponse): string => {
    const parts = []
    if (result.address) parts.push(result.address)
    if (result.city) parts.push(result.city)
    if (result.state) parts.push(result.state)
    if (result.country) parts.push(result.country)
    return parts.join(', ')
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
            <MapPin className="h-4 w-4 shrink-0 opacity-50" />
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
      <PopoverContent className="w-[400px] p-0" align="start">
        {mode === 'select' ? (
          <Command>
            <CommandInput placeholder="Search known locations..." />
            <CommandList className="max-h-[300px]">
              {loadingLocations ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <CommandEmpty>No known locations found.</CommandEmpty>
                  {knownLocations.length > 0 && (
                    <CommandGroup heading="Known Locations">
                      {knownLocations.map((location) => (
                        <CommandItem
                          key={location.guid}
                          value={`${location.name} ${location.city || ''} ${location.country || ''}`}
                          onSelect={() => handleSelectLocation(location)}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              value?.guid === location.guid ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          <div className="flex flex-col flex-1 min-w-0">
                            <span className="truncate font-medium">{location.name}</span>
                            <span className="text-xs text-muted-foreground truncate">
                              {[location.city, location.country].filter(Boolean).join(', ')}
                            </span>
                          </div>
                          {location.timezone && (
                            <span className="text-xs text-muted-foreground ml-2">
                              {location.timezone.split('/').pop()}
                            </span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  )}
                  <CommandSeparator />
                  <CommandGroup>
                    <CommandItem
                      onSelect={() => setMode('new')}
                      className="cursor-pointer"
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      <span>Enter new address...</span>
                    </CommandItem>
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        ) : (
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">New Location</h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMode('select')}
                className="h-8 px-2"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Address Input */}
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">
                Enter full address to lookup
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="123 Main St, City, Country"
                  value={addressInput}
                  onChange={(e) => setAddressInput(e.target.value)}
                  onKeyDown={handleAddressKeyDown}
                  className="flex-1"
                  autoFocus
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleGeocode}
                  disabled={isGeocoding || !addressInput.trim()}
                >
                  {isGeocoding ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Error Message */}
            {geocodeError && (
              <p className="text-sm text-destructive">{geocodeError}</p>
            )}

            {/* Geocode Result */}
            {geocodeResult && (
              <div className="space-y-3 rounded-lg border p-3 bg-muted/50">
                <div className="flex items-start gap-2">
                  <MapPin className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {formatGeocodeResult(geocodeResult)}
                    </p>
                    {geocodeResult.timezone && (
                      <p className="text-xs text-muted-foreground">
                        Timezone: {geocodeResult.timezone}
                      </p>
                    )}
                  </div>
                </div>

                {/* Save as Known Location */}
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="save-as-known"
                    checked={saveAsKnown}
                    onCheckedChange={(checked) => setSaveAsKnown(checked === true)}
                  />
                  <label
                    htmlFor="save-as-known"
                    className="text-sm font-normal cursor-pointer"
                  >
                    Save as known location (reuse in future events)
                  </label>
                </div>

                {/* Use Location Button */}
                <Button
                  onClick={handleCreateLocation}
                  disabled={isCreating}
                  className="w-full"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Use This Location'
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

export default LocationPicker
