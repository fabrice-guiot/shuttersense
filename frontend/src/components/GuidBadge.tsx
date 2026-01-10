/**
 * GuidBadge Component
 *
 * Displays an entity's GUID with copy-to-clipboard functionality.
 * Shows the full ID with a copy icon. Click to copy.
 */

import { Copy, Check } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { useClipboard } from '@/hooks/useClipboard'
import { cn } from '@/lib/utils'

export interface GuidBadgeProps {
  /**
   * The full GUID (e.g., "col_01hgw2bbg00000000000000001")
   */
  guid: string

  /**
   * Optional label to show before the ID
   * @default "ID"
   */
  label?: string

  /**
   * Whether to show the label
   * @default false
   */
  showLabel?: boolean

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * GuidBadge displays a GUID with copy functionality
 *
 * @example
 * <GuidBadge guid="col_01hgw2bbg00000000000000001" />
 *
 * @example With label
 * <GuidBadge guid="col_01hgw2bbg00000000000000001" showLabel label="Collection ID" />
 */
export function GuidBadge({
  guid,
  label = 'ID',
  showLabel = false,
  className,
}: GuidBadgeProps) {
  const { copy, copied } = useClipboard({ resetDelay: 2000 })

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const success = await copy(guid)
    if (success) {
      toast.success('Copied to clipboard', {
        duration: 2000,
      })
    } else {
      toast.error('Failed to copy', {
        description: 'Please try again or copy manually',
      })
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-md',
        className
      )}
      aria-label={`Copy GUID: ${guid}`}
    >
      {showLabel && (
        <span className="text-xs text-muted-foreground">{label}:</span>
      )}
      <Badge
        variant="outline"
        className="font-mono text-xs cursor-pointer hover:bg-muted transition-colors"
      >
        {guid}
        {copied ? (
          <Check className="ml-1.5 h-3 w-3 text-green-500" />
        ) : (
          <Copy className="ml-1.5 h-3 w-3 text-muted-foreground" />
        )}
      </Badge>
    </button>
  )
}

export default GuidBadge
