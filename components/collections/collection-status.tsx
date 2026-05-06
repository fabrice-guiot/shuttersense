"use client"

import { Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Collection } from "@/lib/types"

interface CollectionStatusProps {
  collection: Collection
  showDetails?: boolean
  className?: string
}

export function CollectionStatus({ collection, showDetails = false, className }: CollectionStatusProps) {
  const isAccessible = collection.is_accessible

  // Pending state (null = test in progress)
  if (isAccessible === null) {
    return (
      <Badge variant="secondary" className={cn("gap-1", className)}>
        <Loader2 className="h-3 w-3 animate-spin" />
        Pending
      </Badge>
    )
  }

  const hasErrorDetails = showDetails && !isAccessible && collection.accessibility_message

  // Simple case: just the badge
  if (!hasErrorDetails) {
    return (
      <Badge variant={isAccessible ? "success" : "destructive"} className={className}>
        {isAccessible ? "Accessible" : "Not Accessible"}
      </Badge>
    )
  }

  // With error details
  return (
    <div className={cn("flex flex-col items-start gap-2", className)}>
      <Badge variant="destructive">Not Accessible</Badge>
      <div className="rounded-md px-3 py-2 text-sm bg-red-900/30 text-red-400">
        {collection.accessibility_message}
      </div>
    </div>
  )
}
