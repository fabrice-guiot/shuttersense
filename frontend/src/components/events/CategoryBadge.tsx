/**
 * CategoryBadge Component
 *
 * Displays a category icon with event count badge for compact calendar view.
 * Feature: 016-mobile-calendar-view (GitHub Issue #69)
 */

import { LucideIcon, HelpCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ICON_MAP } from '@/components/settings/CategoryForm'

// ============================================================================
// Constants
// ============================================================================

/** Maximum count to display before showing "99+" */
const MAX_DISPLAY_COUNT = 99

// ============================================================================
// CategoryBadge Component
// ============================================================================

export interface CategoryBadgeProps {
  /** Lucide icon name from ICON_MAP */
  icon: string | null
  /** Category color (hex format, e.g., "#3b82f6") */
  color: string | null
  /** Number of events in this category for the day */
  count: number
  /** Category display name (for tooltip) */
  name: string
  /** Additional CSS classes */
  className?: string
}

export function CategoryBadge({
  icon,
  color,
  count,
  name,
  className,
}: CategoryBadgeProps) {
  // Get icon component or fallback
  const IconComponent: LucideIcon = icon && ICON_MAP[icon] ? ICON_MAP[icon] : HelpCircle
  const displayCount = count > MAX_DISPLAY_COUNT ? '99+' : count.toString()

  return (
    <div
      className={cn(
        'relative inline-flex items-center justify-center',
        'h-5 w-5 rounded-sm',
        className
      )}
      style={{ backgroundColor: color ? `${color}20` : 'var(--muted)' }}
      title={`${count} ${name} event${count !== 1 ? 's' : ''}`}
      role="img"
      aria-label={`${count} ${name} event${count !== 1 ? 's' : ''}`}
    >
      <IconComponent
        className="h-3 w-3"
        style={{ color: color || undefined }}
        aria-hidden="true"
      />
      {count > 1 && (
        <span
          className={cn(
            'absolute -bottom-1 -right-1',
            'min-w-[14px] h-[14px] px-0.5',
            'flex items-center justify-center',
            'text-[10px] font-medium leading-none',
            'bg-background border border-border rounded-full'
          )}
          aria-hidden="true"
        >
          {displayCount}
        </span>
      )}
    </div>
  )
}
