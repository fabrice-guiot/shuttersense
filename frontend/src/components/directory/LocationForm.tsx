/**
 * Location Form Component
 *
 * Form for creating and editing event locations.
 * Supports geocoding addresses to auto-fill coordinates and timezone.
 * Issue #39 - Calendar Events feature (Phase 8)
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ChevronDown, ChevronRight, Loader2, MapPin, Search, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { TimezoneCombobox } from '@/components/ui/timezone-combobox'
import type { Location, GeocodeResponse } from '@/contracts/api/location-api'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Form Schema
// ============================================================================

const locationFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  category_guid: z.string().min(1, 'Category is required'),
  address: z.string().max(500).optional().nullable(),
  city: z.string().max(100).optional().nullable(),
  state: z.string().max(100).optional().nullable(),
  country: z.string().max(100).optional().nullable(),
  postal_code: z.string().max(20).optional().nullable(),
  latitude: z.number().min(-90).max(90).optional().nullable(),
  longitude: z.number().min(-180).max(180).optional().nullable(),
  timezone: z.string().max(64).optional().nullable(),
  rating: z.number().min(1).max(5).optional().nullable(),
  timeoff_required_default: z.boolean(),
  travel_required_default: z.boolean(),
  notes: z.string().optional().nullable(),
  is_known: z.boolean(),
})

type LocationFormData = z.infer<typeof locationFormSchema>

// ============================================================================
// Rating Selector Component
// ============================================================================

interface RatingSelectorProps {
  value: number | null
  onChange: (value: number | null) => void
}

function RatingSelector({ value, onChange }: RatingSelectorProps) {
  const [hovered, setHovered] = useState<number | null>(null)

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 5 }).map((_, i) => {
        const starValue = i + 1
        const isActive = (hovered !== null ? hovered : value) !== null &&
          starValue <= (hovered !== null ? hovered : (value || 0))

        return (
          <button
            key={i}
            type="button"
            onClick={() => onChange(value === starValue ? null : starValue)}
            onMouseEnter={() => setHovered(starValue)}
            onMouseLeave={() => setHovered(null)}
            className="p-0.5 hover:scale-110 transition-transform"
          >
            <Star
              className={cn(
                'h-5 w-5 transition-colors',
                isActive
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'text-muted-foreground/30 hover:text-yellow-400/50'
              )}
            />
          </button>
        )
      })}
      {value !== null && (
        <button
          type="button"
          onClick={() => onChange(null)}
          className="ml-2 text-xs text-muted-foreground hover:text-foreground"
        >
          Clear
        </button>
      )}
    </div>
  )
}

// ============================================================================
// Form Component
// ============================================================================

interface LocationFormProps {
  /** Location to edit (null for create mode) */
  location?: Location | null
  /** Available categories for selection */
  categories: Category[]
  /** Called when form is submitted */
  onSubmit: (data: LocationFormData) => Promise<void>
  /** Called when cancel is clicked */
  onCancel: () => void
  /** Called to geocode an address */
  onGeocode?: (address: string) => Promise<GeocodeResponse | null>
  /** Whether form is submitting */
  isSubmitting?: boolean
}

export function LocationForm({
  location,
  categories,
  onSubmit,
  onCancel,
  onGeocode,
  isSubmitting = false
}: LocationFormProps) {
  const isEditMode = !!location
  const [isGeocoding, setIsGeocoding] = useState(false)
  const [fullAddressInput, setFullAddressInput] = useState('')
  const [showAddressDetails, setShowAddressDetails] = useState(false)

  // Filter to only active categories for new locations
  const availableCategories = isEditMode
    ? categories
    : categories.filter(c => c.is_active)

  const form = useForm<LocationFormData>({
    resolver: zodResolver(locationFormSchema),
    defaultValues: {
      name: '',
      category_guid: '',
      address: null,
      city: null,
      state: null,
      country: null,
      postal_code: null,
      latitude: null,
      longitude: null,
      timezone: null,
      rating: null,
      timeoff_required_default: false,
      travel_required_default: false,
      notes: null,
      is_known: true,
    }
  })

  // Populate form when editing
  useEffect(() => {
    if (location) {
      form.reset({
        name: location.name,
        category_guid: location.category.guid,
        address: location.address,
        city: location.city,
        state: location.state,
        country: location.country,
        postal_code: location.postal_code,
        latitude: location.latitude,
        longitude: location.longitude,
        timezone: location.timezone,
        rating: location.rating,
        timeoff_required_default: location.timeoff_required_default,
        travel_required_default: location.travel_required_default,
        notes: location.notes,
        is_known: location.is_known,
      })
      // Show address details if any address field is populated
      if (location.address || location.city || location.state || location.country || location.postal_code) {
        setShowAddressDetails(true)
      }
    }
  }, [location, form])

  // Handle geocoding from full address input
  const handleGeocode = async () => {
    if (!fullAddressInput.trim() || !onGeocode) return

    setIsGeocoding(true)
    try {
      const result = await onGeocode(fullAddressInput.trim())
      if (result) {
        // Update form with geocoded values - populate individual fields
        form.setValue('address', result.address || null)
        form.setValue('city', result.city || null)
        form.setValue('state', result.state || null)
        form.setValue('country', result.country || null)
        form.setValue('postal_code', result.postal_code || null)
        form.setValue('latitude', result.latitude)
        form.setValue('longitude', result.longitude)
        if (result.timezone) form.setValue('timezone', result.timezone)
        // Show address details and clear the lookup field
        setShowAddressDetails(true)
        setFullAddressInput('')
      }
    } finally {
      setIsGeocoding(false)
    }
  }

  // Handle Enter key in full address input
  const handleAddressKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleGeocode()
    }
  }

  const handleFormSubmit = async (data: LocationFormData) => {
    // Clean up empty strings to null
    const cleanedData = {
      ...data,
      address: data.address || null,
      city: data.city || null,
      state: data.state || null,
      country: data.country || null,
      postal_code: data.postal_code || null,
      timezone: data.timezone || null,
      notes: data.notes || null,
    }
    await onSubmit(cleanedData)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleFormSubmit)} className="space-y-4">
        {/* Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name *</FormLabel>
              <FormControl>
                <Input placeholder="Location name" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Category */}
        <FormField
          control={form.control}
          name="category_guid"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Category *</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {availableCategories.map(category => (
                    <SelectItem key={category.guid} value={category.guid}>
                      <span className="flex items-center gap-2">
                        {category.color && (
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                        )}
                        {category.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Events using this location must have the same category
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Address Lookup */}
        {onGeocode && (
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Address Lookup</label>
            <div className="flex gap-2">
              <Input
                placeholder="Enter full address to lookup..."
                value={fullAddressInput}
                onChange={(e) => setFullAddressInput(e.target.value)}
                onKeyDown={handleAddressKeyDown}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleGeocode}
                disabled={isGeocoding || !fullAddressInput.trim()}
                className="gap-2"
              >
                {isGeocoding ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Lookup
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Enter an address and click Lookup to auto-fill the fields below
            </p>
          </div>
        )}

        {/* Address Details (Collapsible) */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setShowAddressDetails(!showAddressDetails)}
            className="flex items-center gap-2 text-sm font-medium hover:text-foreground text-muted-foreground"
          >
            {showAddressDetails ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            Address Details
            {!showAddressDetails && (form.getValues('city') || form.getValues('country')) && (
              <span className="font-normal">
                — {[form.getValues('city'), form.getValues('country')].filter(Boolean).join(', ')}
              </span>
            )}
          </button>

          {showAddressDetails && (
            <div className="space-y-3 pl-6 border-l-2 border-muted">
              <FormField
                control={form.control}
                name="address"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Street Address</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="123 Main Street"
                        {...field}
                        value={field.value || ''}
                        onChange={(e) => field.onChange(e.target.value || null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="City"
                          {...field}
                          value={field.value || ''}
                          onChange={(e) => field.onChange(e.target.value || null)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="state"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>State/Province</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="State"
                          {...field}
                          value={field.value || ''}
                          onChange={(e) => field.onChange(e.target.value || null)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="country"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Country</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Country"
                          {...field}
                          value={field.value || ''}
                          onChange={(e) => field.onChange(e.target.value || null)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="postal_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Postal Code</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="12345"
                          {...field}
                          value={field.value || ''}
                          onChange={(e) => field.onChange(e.target.value || null)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
          )}
        </div>

        {/* Coordinates */}
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="latitude"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Latitude</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="any"
                    placeholder="40.7128"
                    {...field}
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="longitude"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Longitude</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    step="any"
                    placeholder="-74.0060"
                    {...field}
                    value={field.value ?? ''}
                    onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Timezone */}
        <FormField
          control={form.control}
          name="timezone"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Timezone</FormLabel>
              <FormControl>
                <TimezoneCombobox
                  value={field.value || ''}
                  onChange={field.onChange}
                  placeholder="Select timezone (optional)"
                />
              </FormControl>
              <FormDescription>
                Used for displaying event times at this location
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Rating */}
        <FormField
          control={form.control}
          name="rating"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Rating</FormLabel>
              <FormControl>
                <RatingSelector
                  value={field.value}
                  onChange={field.onChange}
                />
              </FormControl>
              <FormDescription>
                Your rating of this venue (optional)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Default Settings */}
        <div className="space-y-3 rounded-lg border p-4">
          <h4 className="text-sm font-medium">Default Settings for New Events</h4>
          <p className="text-sm text-muted-foreground">
            These settings will be pre-selected when creating events at this location
          </p>

          <FormField
            control={form.control}
            name="timeoff_required_default"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <FormLabel className="font-normal">
                  Time-off required
                </FormLabel>
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="travel_required_default"
            render={({ field }) => (
              <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <FormLabel className="font-normal">
                  Travel required
                </FormLabel>
              </FormItem>
            )}
          />
        </div>

        {/* Notes */}
        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Additional notes about this location"
                  className="resize-none"
                  rows={3}
                  {...field}
                  value={field.value || ''}
                  onChange={(e) => field.onChange(e.target.value || null)}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Known Location Toggle */}
        <FormField
          control={form.control}
          name="is_known"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center space-x-3 space-y-0">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel className="font-normal">
                  Save as known location
                </FormLabel>
                <FormDescription>
                  Known locations appear in the location picker when creating events
                </FormDescription>
              </div>
            </FormItem>
          )}
        />

        {/* Form Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || isGeocoding}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEditMode ? 'Save Changes' : 'Create Location'}
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default LocationForm
