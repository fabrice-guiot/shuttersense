/**
 * Organizer Form Component
 *
 * Form for creating and editing event organizers.
 * Issue #39 - Calendar Events feature (Phase 9)
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, Star } from 'lucide-react'
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
import type { Organizer } from '@/contracts/api/organizer-api'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Form Schema
// ============================================================================

const organizerFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  category_guid: z.string().min(1, 'Category is required'),
  website: z.string().max(500).optional().nullable(),
  rating: z.number().min(1).max(5).optional().nullable(),
  ticket_required_default: z.boolean(),
  notes: z.string().optional().nullable(),
})

type OrganizerFormData = z.infer<typeof organizerFormSchema>

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

interface OrganizerFormProps {
  /** Organizer to edit (null for create mode) */
  organizer?: Organizer | null
  /** Available categories for selection */
  categories: Category[]
  /** Called when form is submitted */
  onSubmit: (data: OrganizerFormData) => Promise<void>
  /** Called when cancel is clicked */
  onCancel: () => void
  /** Whether form is submitting */
  isSubmitting?: boolean
}

export function OrganizerForm({
  organizer,
  categories,
  onSubmit,
  onCancel,
  isSubmitting = false
}: OrganizerFormProps) {
  const isEditMode = !!organizer
  const [submitting, setSubmitting] = useState(false)

  // Filter to only active categories for new organizers
  const availableCategories = isEditMode
    ? categories
    : categories.filter(c => c.is_active)

  const form = useForm<OrganizerFormData>({
    resolver: zodResolver(organizerFormSchema),
    defaultValues: {
      name: organizer?.name || '',
      category_guid: organizer?.category.guid || '',
      website: organizer?.website || '',
      rating: organizer?.rating || null,
      ticket_required_default: organizer?.ticket_required_default || false,
      notes: organizer?.notes || '',
    }
  })

  const handleSubmit = async (data: OrganizerFormData) => {
    setSubmitting(true)
    try {
      // Clean up empty strings to null
      const cleanedData = {
        ...data,
        website: data.website?.trim() || null,
        notes: data.notes?.trim() || null,
      }
      await onSubmit(cleanedData)
    } finally {
      setSubmitting(false)
    }
  }

  const isLoading = submitting || isSubmitting

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
        {/* Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name *</FormLabel>
              <FormControl>
                <Input
                  placeholder="e.g., Live Nation, AEG Presents"
                  {...field}
                />
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
              <Select
                value={field.value}
                onValueChange={field.onChange}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {availableCategories.map((category) => (
                    <SelectItem key={category.guid} value={category.guid}>
                      <div className="flex items-center gap-2">
                        {category.color && (
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: category.color }}
                          />
                        )}
                        <span>{category.name}</span>
                        {!category.is_active && (
                          <span className="text-xs text-muted-foreground">(inactive)</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Organizer will only appear for events in this category
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Website */}
        <FormField
          control={form.control}
          name="website"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Website</FormLabel>
              <FormControl>
                <Input
                  placeholder="e.g., https://example.com"
                  {...field}
                  value={field.value || ''}
                />
              </FormControl>
              <FormDescription>
                Link to organizer's official website
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
                Rate this organizer to help prioritize events
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Ticket Required Default */}
        <FormField
          control={form.control}
          name="ticket_required_default"
          render={({ field }) => (
            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel>
                  Ticket required by default
                </FormLabel>
                <FormDescription>
                  New events by this organizer will have "ticket required" pre-selected
                </FormDescription>
              </div>
            </FormItem>
          )}
        />

        {/* Notes */}
        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Additional notes about this organizer..."
                  className="resize-none"
                  rows={3}
                  {...field}
                  value={field.value || ''}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Form Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEditMode ? 'Save Changes' : 'Create Organizer'}
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default OrganizerForm
