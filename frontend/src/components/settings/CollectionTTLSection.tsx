/**
 * Collection TTL Section Component
 *
 * Manages collection cache TTL configuration per collection state.
 * TTL values determine how long collection file listings are cached.
 *
 * Part of Collection TTL Team-Level Configuration Refactor.
 */

import { useState } from 'react'
import { Clock, Pencil, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import type { CollectionTTLConfig } from '@/contracts/api/config-api'

// ============================================================================
// Types
// ============================================================================

interface CollectionTTLSectionProps {
  /** TTL configuration from backend */
  ttlConfig: Record<string, CollectionTTLConfig>
  /** Loading state */
  loading?: boolean
  /** Called when a TTL value is updated */
  onUpdate: (key: string, value: { value: number; label: string }) => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

const STATE_DESCRIPTIONS: Record<string, string> = {
  live: 'Active work in progress, frequent changes',
  closed: 'Finished work, infrequent changes',
  archived: 'Long-term storage, minimal changes'
}

const STATE_ORDER = ['live', 'closed', 'archived']

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format seconds to human-readable duration
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} second${seconds !== 1 ? 's' : ''}`
  }

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`
  }

  const hours = Math.floor(minutes / 60)
  if (hours < 24) {
    return `${hours} hour${hours !== 1 ? 's' : ''}`
  }

  const days = Math.floor(hours / 24)
  return `${days} day${days !== 1 ? 's' : ''}`
}

/**
 * Parse duration input to seconds
 * Supports formats: "1h", "24h", "7d", "3600", "1 hour", "24 hours", "7 days"
 */
function parseDuration(input: string): number | null {
  const trimmed = input.trim().toLowerCase()

  // Try direct number (seconds)
  const directNum = parseInt(trimmed, 10)
  if (!isNaN(directNum) && String(directNum) === trimmed) {
    return directNum
  }

  // Try short format: 1h, 24h, 7d
  const shortMatch = trimmed.match(/^(\d+)(h|d)$/)
  if (shortMatch) {
    const value = parseInt(shortMatch[1], 10)
    const unit = shortMatch[2]
    if (unit === 'h') return value * 3600
    if (unit === 'd') return value * 86400
  }

  // Try long format: 1 hour, 24 hours, 7 days
  const longMatch = trimmed.match(/^(\d+)\s*(hours?|days?|minutes?)$/)
  if (longMatch) {
    const value = parseInt(longMatch[1], 10)
    const unit = longMatch[2]
    if (unit.startsWith('hour')) return value * 3600
    if (unit.startsWith('day')) return value * 86400
    if (unit.startsWith('minute')) return value * 60
  }

  return null
}

// ============================================================================
// Component
// ============================================================================

export function CollectionTTLSection({
  ttlConfig,
  loading = false,
  onUpdate
}: CollectionTTLSectionProps) {
  // Dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Edit form state
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [ttlInput, setTtlInput] = useState('')

  // Convert to sorted array
  const ttlList = STATE_ORDER.map(key => {
    const config = ttlConfig[key]
    return {
      key,
      value: config?.value ?? getDefaultTTL(key),
      label: config?.label ?? `${key.charAt(0).toUpperCase() + key.slice(1)} (default)`
    }
  })

  // Open edit dialog
  const handleEdit = (key: string) => {
    const config = ttlConfig[key]
    setEditingKey(key)
    setTtlInput(config?.value?.toString() ?? '')
    setFormError(null)
    setEditDialogOpen(true)
  }

  // Handle save
  const handleSave = async () => {
    if (!editingKey) return

    if (!ttlInput.trim()) {
      setFormError('TTL value is required')
      return
    }

    const seconds = parseDuration(ttlInput)
    if (seconds === null || seconds < 0) {
      setFormError('Invalid duration. Use formats like "1h", "24h", "7d", or seconds.')
      return
    }

    if (seconds === 0) {
      setFormError('TTL must be greater than 0')
      return
    }

    if (seconds > 604800) {
      setFormError('TTL cannot exceed 7 days (604800 seconds)')
      return
    }

    setIsSubmitting(true)
    setFormError(null)

    try {
      const stateName = editingKey.charAt(0).toUpperCase() + editingKey.slice(1)
      await onUpdate(editingKey, {
        value: seconds,
        label: `${stateName} (${formatDuration(seconds)})`
      })
      setEditDialogOpen(false)
    } catch (err: any) {
      setFormError(err.userMessage || err.message || 'Update failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle className="text-lg">Collection Cache TTL</CardTitle>
            <CardDescription>
              Configure cache duration for collection file listings by state
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>State</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Cache Duration</TableHead>
                <TableHead className="w-16">Edit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ttlList.map((item) => (
                <TableRow key={item.key}>
                  <TableCell>
                    <Badge variant="secondary" className="capitalize">
                      {item.key}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {STATE_DESCRIPTIONS[item.key]}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono">
                      {formatDuration(item.value)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(item.key)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={() => setEditDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Edit Cache TTL for {editingKey?.charAt(0).toUpperCase()}{editingKey?.slice(1)} Collections
            </DialogTitle>
            <DialogDescription>
              Set how long file listings are cached for {editingKey} collections.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ttlValue">Cache Duration</Label>
              <Input
                id="ttlValue"
                value={ttlInput}
                onChange={e => setTtlInput(e.target.value)}
                placeholder="e.g., 1h, 24h, 7d, or 3600"
              />
              <p className="text-xs text-muted-foreground">
                Enter duration as: "1h" (1 hour), "24h" (24 hours), "7d" (7 days), or seconds.
                Maximum: 7 days.
              </p>
            </div>

            {formError && (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

// ============================================================================
// Helper - Default TTL values
// ============================================================================

function getDefaultTTL(state: string): number {
  switch (state) {
    case 'live': return 3600      // 1 hour
    case 'closed': return 86400   // 24 hours
    case 'archived': return 604800 // 7 days
    default: return 3600
  }
}

export default CollectionTTLSection
