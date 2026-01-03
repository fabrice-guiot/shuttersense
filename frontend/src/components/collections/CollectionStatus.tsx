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

  const hasErrorDetails = showDetails && !isAccessible && collection.accessibility_message

  // Simple case: just the badge
  if (!hasErrorDetails) {
    return (
      <Badge variant={isAccessible ? 'success' : 'destructive'} className={className}>
        {isAccessible ? 'Accessible' : 'Not Accessible'}
      </Badge>
    )
  }

  // With error details
  return (
    <div className={cn('flex flex-col items-start gap-2', className)}>
      <Badge variant="destructive">
        Not Accessible
      </Badge>
      <div className="rounded-md px-3 py-2 text-sm bg-red-900/30 text-red-400">
        {collection.accessibility_message}
      </div>
    </div>
  )
}
