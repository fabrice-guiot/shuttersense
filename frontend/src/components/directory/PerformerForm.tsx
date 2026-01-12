/**
 * Performer Form Component
 *
 * Form for creating and editing event performers.
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import type { Performer } from '@/contracts/api/performer-api'
import type { Category } from '@/contracts/api/category-api'

// ============================================================================
// Form Schema
// ============================================================================

const performerFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  category_guid: z.string().min(1, 'Category is required'),
  website: z.string().max(500).optional().nullable(),
  instagram_handle: z.string().max(100).optional().nullable(),
  additional_info: z.string().optional().nullable(),
})

type PerformerFormData = z.infer<typeof performerFormSchema>

// ============================================================================
// Form Component
// ============================================================================

interface PerformerFormProps {
  /** Performer to edit (null for create mode) */
  performer?: Performer | null
  /** Available categories for selection */
  categories: Category[]
  /** Called when form is submitted */
  onSubmit: (data: PerformerFormData) => Promise<void>
  /** Called when cancel is clicked */
  onCancel: () => void
  /** Whether form is submitting */
  isSubmitting?: boolean
}

export function PerformerForm({
  performer,
  categories,
  onSubmit,
  onCancel,
  isSubmitting = false
}: PerformerFormProps) {
  const isEditMode = !!performer
  const [submitting, setSubmitting] = useState(false)

  // Filter to only active categories for new performers
  const availableCategories = isEditMode
    ? categories
    : categories.filter(c => c.is_active)

  const form = useForm<PerformerFormData>({
    resolver: zodResolver(performerFormSchema),
    defaultValues: {
      name: performer?.name || '',
      category_guid: performer?.category.guid || '',
      website: performer?.website || '',
      instagram_handle: performer?.instagram_handle || '',
      additional_info: performer?.additional_info || '',
    }
  })

  const handleSubmit = async (data: PerformerFormData) => {
    setSubmitting(true)
    try {
      // Clean up empty strings to null and strip @ from instagram
      const cleanedData = {
        ...data,
        website: data.website?.trim() || null,
        instagram_handle: data.instagram_handle?.trim()?.replace(/^@/, '') || null,
        additional_info: data.additional_info?.trim() || null,
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
                  placeholder="e.g., Blue Angels, Thunderbirds"
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
                Performer will only appear for events in this category
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
                Link to performer's official website
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Instagram Handle */}
        <FormField
          control={form.control}
          name="instagram_handle"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Instagram Handle</FormLabel>
              <FormControl>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    @
                  </span>
                  <Input
                    placeholder="username"
                    className="pl-7"
                    {...field}
                    value={field.value?.replace(/^@/, '') || ''}
                  />
                </div>
              </FormControl>
              <FormDescription>
                Instagram username (without the @)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Additional Info */}
        <FormField
          control={form.control}
          name="additional_info"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Additional Info</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Additional notes about this performer..."
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
            {isEditMode ? 'Save Changes' : 'Create Performer'}
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default PerformerForm
