import { Badge } from '@/components/ui/badge'
import type { CollectionStatusProps } from '@/contracts/components/collection-components'
import { cn } from '@/lib/utils'

/**
 * Collection status component
 * Displays accessibility status with optional error details
 */
export function CollectionStatus({
  collection,
  showDetails = false,
  className
}: CollectionStatusProps) {
  const isAccessible = collection.is_accessible

  // Status configuration
  const statusConfig = isAccessible
    ? {
        badgeVariant: 'default' as const,
        dotColor: 'bg-green-400',
        badgeText: 'Accessible',
        backgroundColor: 'bg-green-900/30',
        textColor: 'text-green-400'
      }
    : {
        badgeVariant: 'destructive' as const,
        dotColor: 'bg-red-400',
        badgeText: 'Not Accessible',
        backgroundColor: 'bg-red-900/30',
        textColor: 'text-red-400'
      }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Status Badge */}
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'h-2 w-2 rounded-full',
            statusConfig.dotColor
          )}
          aria-hidden="true"
        />
        <Badge variant={statusConfig.badgeVariant}>
          {statusConfig.badgeText}
        </Badge>
      </div>

      {/* Error Details (if requested and available) */}
      {showDetails && !isAccessible && collection.accessibility_message && (
        <div
          className={cn(
            'rounded-md px-3 py-2 text-sm',
            statusConfig.backgroundColor,
            statusConfig.textColor
          )}
        >
          {collection.accessibility_message}
        </div>
      )}
    </div>
  )
}
