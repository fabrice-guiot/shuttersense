/**
 * Category Form Component
 *
 * Form for creating and editing event categories.
 * Issue #39 - Calendar Events feature (Phase 3)
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Loader2,
  // Event & Entertainment
  Plane,
  Music,
  Ticket,
  PartyPopper,
  Sparkles,
  // Nature & Wildlife
  Bird,
  Trees,
  Flower2,
  Sun,
  Mountain,
  // People & Social
  Heart,
  Users,
  Baby,
  GraduationCap,
  // Sports & Competition
  Trophy,
  Medal,
  Flag,
  Target,
  // Media & Art
  Camera,
  Film,
  Palette,
  Mic,
  // Travel & Transport
  Car,
  Ship,
  Train,
  // Other
  Star,
  Gem,
  Crown,
  Briefcase,
  Calendar,
  type LucideIcon
} from 'lucide-react'
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
import { Checkbox } from '@/components/ui/checkbox'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Available Icons
// ============================================================================

interface IconOption {
  name: string
  icon: LucideIcon
  label: string
}

/**
 * Curated list of icons suitable for event categories.
 * Organized by theme for easy browsing.
 */
export const AVAILABLE_ICONS: IconOption[] = [
  // Event & Entertainment
  { name: 'plane', icon: Plane, label: 'Plane' },
  { name: 'music', icon: Music, label: 'Music' },
  { name: 'ticket', icon: Ticket, label: 'Ticket' },
  { name: 'party-popper', icon: PartyPopper, label: 'Party' },
  { name: 'sparkles', icon: Sparkles, label: 'Sparkles' },
  // Nature & Wildlife
  { name: 'bird', icon: Bird, label: 'Bird' },
  { name: 'trees', icon: Trees, label: 'Trees' },
  { name: 'flower-2', icon: Flower2, label: 'Flower' },
  { name: 'sun', icon: Sun, label: 'Sun' },
  { name: 'mountain', icon: Mountain, label: 'Mountain' },
  // People & Social
  { name: 'heart', icon: Heart, label: 'Heart' },
  { name: 'users', icon: Users, label: 'Users' },
  { name: 'baby', icon: Baby, label: 'Baby' },
  { name: 'graduation-cap', icon: GraduationCap, label: 'Graduation' },
  // Sports & Competition
  { name: 'trophy', icon: Trophy, label: 'Trophy' },
  { name: 'medal', icon: Medal, label: 'Medal' },
  { name: 'flag', icon: Flag, label: 'Flag' },
  { name: 'target', icon: Target, label: 'Target' },
  // Media & Art
  { name: 'camera', icon: Camera, label: 'Camera' },
  { name: 'film', icon: Film, label: 'Film' },
  { name: 'palette', icon: Palette, label: 'Art' },
  { name: 'mic', icon: Mic, label: 'Microphone' },
  // Travel & Transport
  { name: 'car', icon: Car, label: 'Car' },
  { name: 'ship', icon: Ship, label: 'Ship' },
  { name: 'train', icon: Train, label: 'Train' },
  // Other
  { name: 'star', icon: Star, label: 'Star' },
  { name: 'gem', icon: Gem, label: 'Gem' },
  { name: 'crown', icon: Crown, label: 'Crown' },
  { name: 'briefcase', icon: Briefcase, label: 'Business' },
  { name: 'calendar', icon: Calendar, label: 'Calendar' },
]

/**
 * Map of icon names to their components for quick lookup.
 */
export const ICON_MAP: Record<string, LucideIcon> = Object.fromEntries(
  AVAILABLE_ICONS.map(({ name, icon }) => [name, icon])
)

// ============================================================================
// Form Schema
// ============================================================================

const categoryFormSchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .max(100, 'Name must be 100 characters or less'),
  is_active: z.boolean(),
  icon: z.string()
    .max(50, 'Icon must be 50 characters or less')
    .nullable()
    .optional()
    .transform(val => val === '' ? null : val),
  color: z.string()
    .regex(/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/, {
      message: 'Color must be a valid hex code (e.g., #FF0000 or #F00)'
    })
    .nullable()
    .optional()
    .or(z.literal(''))
    .transform(val => val === '' ? null : val)
})

type CategoryFormData = z.infer<typeof categoryFormSchema>

// ============================================================================
// Component Props
// ============================================================================

export interface CategoryFormProps {
  category?: Category | null
  onSubmit: (data: CategoryFormData) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

// ============================================================================
// Preset Colors
// ============================================================================

const PRESET_COLORS = [
  { name: 'Blue', value: '#3B82F6' },
  { name: 'Green', value: '#22C55E' },
  { name: 'Pink', value: '#EC4899' },
  { name: 'Orange', value: '#F97316' },
  { name: 'Purple', value: '#8B5CF6' },
  { name: 'Red', value: '#EF4444' },
  { name: 'Gray', value: '#6B7280' },
  { name: 'Teal', value: '#14B8A6' },
]

// ============================================================================
// Component
// ============================================================================

export function CategoryForm({
  category,
  onSubmit,
  onCancel,
  loading = false
}: CategoryFormProps) {
  const isEdit = !!category

  // Initialize form with react-hook-form and Zod
  const form = useForm<CategoryFormData>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: {
      name: category?.name || '',
      icon: category?.icon || '',
      color: category?.color || '',
      is_active: category?.is_active ?? true
    }
  })

  // Update form when category prop changes
  useEffect(() => {
    if (category) {
      form.reset({
        name: category.name,
        icon: category.icon || '',
        color: category.color || '',
        is_active: category.is_active
      })
    }
  }, [category, form])

  const handleSubmit = async (data: CategoryFormData) => {
    await onSubmit(data)
  }

  const selectedColor = form.watch('color')
  const selectedIcon = form.watch('icon')

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        {/* Name Field */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input
                  placeholder="e.g., Airshow, Wedding, Wildlife"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Icon Field - Visual Picker */}
        <FormField
          control={form.control}
          name="icon"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Icon</FormLabel>
              <FormControl>
                <TooltipProvider delayDuration={300}>
                  <div className="grid grid-cols-10 gap-1">
                    {AVAILABLE_ICONS.map(({ name, icon: IconComponent, label }) => {
                      const isSelected = field.value === name
                      return (
                        <Tooltip key={name}>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              onClick={() => {
                                // Toggle: click again to deselect
                                field.onChange(isSelected ? '' : name)
                              }}
                              className={cn(
                                'h-8 w-8 flex items-center justify-center rounded-md border transition-all',
                                isSelected
                                  ? 'border-primary bg-primary/10 text-primary ring-2 ring-primary ring-offset-1'
                                  : 'border-border hover:border-primary/50 hover:bg-muted text-muted-foreground hover:text-foreground'
                              )}
                            >
                              <IconComponent className="h-4 w-4" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="text-xs">
                            {label}
                          </TooltipContent>
                        </Tooltip>
                      )
                    })}
                  </div>
                </TooltipProvider>
              </FormControl>
              {selectedIcon && (
                <FormDescription>
                  Selected: {AVAILABLE_ICONS.find(i => i.name === selectedIcon)?.label || selectedIcon}
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Color Field */}
        <FormField
          control={form.control}
          name="color"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Color</FormLabel>
              <div className="flex gap-2 items-center">
                <FormControl>
                  <Input
                    placeholder="#3B82F6"
                    {...field}
                    value={field.value || ''}
                    className="flex-1"
                  />
                </FormControl>
                {selectedColor && (
                  <div
                    className="h-9 w-9 rounded-md border shrink-0"
                    style={{ backgroundColor: selectedColor }}
                  />
                )}
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {PRESET_COLORS.map(({ name, value }) => (
                  <button
                    key={value}
                    type="button"
                    title={name}
                    className={cn(
                      'h-6 w-6 rounded-full border-2 transition-colors',
                      field.value === value
                        ? 'border-foreground scale-110'
                        : 'border-transparent hover:border-foreground/50'
                    )}
                    style={{ backgroundColor: value }}
                    onClick={() => form.setValue('color', value)}
                  />
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Active Status */}
        <FormField
          control={form.control}
          name="is_active"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center space-x-3 space-y-0 rounded-lg border p-3">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <div className="space-y-0.5">
                <FormLabel className="font-normal">Active</FormLabel>
                <FormDescription>
                  Inactive categories won't appear in dropdowns
                </FormDescription>
              </div>
            </FormItem>
          )}
        />

        {/* Form Actions */}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEdit ? 'Update' : 'Create'}
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default CategoryForm
