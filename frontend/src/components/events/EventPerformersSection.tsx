/**
 * Event Performers Section Component
 *
 * Manages performers associated with an event.
 * Displays performer list with status and allows add/remove/status updates.
 *
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Plus, Users, Instagram, X, Check, Ban, Megaphone, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { PerformerPicker } from './PerformerPicker'
import {
  addPerformerToEvent,
  updateEventPerformerStatus,
  removePerformerFromEvent,
} from '@/services/events'
import type { Performer } from '@/contracts/api/performer-api'
import type { PerformerSummary, PerformerStatus } from '@/contracts/api/event-api'

// ============================================================================
// Types
// ============================================================================

export interface EventPerformersSectionProps {
  /** Event GUID */
  eventGuid: string
  /** Category GUID for filtering performers */
  categoryGuid: string | null
  /** Current performers from EventDetail (summary format) */
  performers: PerformerSummary[]
  /** Whether editing is enabled */
  editable?: boolean
  /** Whether the event is part of a series (for showing sync notice) */
  isSeriesEvent?: boolean
  /** Called when performers are updated */
  onPerformersChange?: () => void
}

// ============================================================================
// Status Badge Component
// ============================================================================

function PerformerStatusBadge({ status }: { status: PerformerStatus }) {
  switch (status) {
    case 'announced':
      return (
        <Badge variant="outline" className="gap-1 text-blue-600 border-blue-600/30 bg-blue-500/10">
          <Megaphone className="h-3 w-3" />
          Announced
        </Badge>
      )
    case 'confirmed':
      return (
        <Badge variant="outline" className="gap-1 text-green-600 border-green-600/30 bg-green-500/10">
          <Check className="h-3 w-3" />
          Confirmed
        </Badge>
      )
    case 'cancelled':
      return (
        <Badge variant="outline" className="gap-1 text-red-600 border-red-600/30 bg-red-500/10">
          <Ban className="h-3 w-3" />
          Cancelled
        </Badge>
      )
  }
}

// ============================================================================
// Component
// ============================================================================

export function EventPerformersSection({
  eventGuid,
  categoryGuid,
  performers,
  editable = false,
  isSeriesEvent = false,
  onPerformersChange,
}: EventPerformersSectionProps) {
  // State for adding performer
  const [isAddingPerformer, setIsAddingPerformer] = useState(false)
  const [selectedPerformer, setSelectedPerformer] = useState<Performer | null>(null)
  const [addLoading, setAddLoading] = useState(false)

  // State for removing performer
  const [removePerformer, setRemovePerformer] = useState<PerformerSummary | null>(null)
  const [removeLoading, setRemoveLoading] = useState(false)

  // State for updating status
  const [statusLoading, setStatusLoading] = useState<string | null>(null)

  // Get GUIDs of performers already added
  const addedPerformerGuids = performers.map(p => p.guid)

  // Handle adding a performer
  const handleAddPerformer = async () => {
    if (!selectedPerformer) return

    setAddLoading(true)
    try {
      await addPerformerToEvent(eventGuid, selectedPerformer.guid, 'confirmed')
      toast.success(`Added ${selectedPerformer.name} to event`)
      setSelectedPerformer(null)
      setIsAddingPerformer(false)
      onPerformersChange?.()
    } catch (err: any) {
      toast.error('Failed to add performer', {
        description: err.userMessage || 'An error occurred',
      })
    } finally {
      setAddLoading(false)
    }
  }

  // Handle updating performer status
  const handleStatusChange = async (performerGuid: string, newStatus: PerformerStatus) => {
    setStatusLoading(performerGuid)
    try {
      await updateEventPerformerStatus(eventGuid, performerGuid, newStatus)
      toast.success('Performer status updated')
      onPerformersChange?.()
    } catch (err: any) {
      toast.error('Failed to update status', {
        description: err.userMessage || 'An error occurred',
      })
    } finally {
      setStatusLoading(null)
    }
  }

  // Handle removing a performer
  const handleRemovePerformer = async () => {
    if (!removePerformer) return

    setRemoveLoading(true)
    try {
      await removePerformerFromEvent(eventGuid, removePerformer.guid)
      toast.success(`Removed ${removePerformer.name} from event`)
      setRemovePerformer(null)
      onPerformersChange?.()
    } catch (err: any) {
      toast.error('Failed to remove performer', {
        description: err.userMessage || 'An error occurred',
      })
    } finally {
      setRemoveLoading(false)
    }
  }

  // Cancel adding
  const handleCancelAdd = () => {
    setSelectedPerformer(null)
    setIsAddingPerformer(false)
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Users className="h-4 w-4" />
          <span>Performers</span>
          {performers.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {performers.length}
            </Badge>
          )}
        </div>
        {editable && !isAddingPerformer && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1"
            onClick={() => setIsAddingPerformer(true)}
          >
            <Plus className="h-3 w-3" />
            Add
          </Button>
        )}
      </div>

      {/* Series sync notice */}
      {editable && isSeriesEvent && (
        <p className="text-xs text-muted-foreground">
          Adding or removing performers applies to all events in the series. Status can be set per event.
        </p>
      )}

      {/* Add Performer Section */}
      {isAddingPerformer && (
        <div className="flex gap-2 items-start">
          <div className="flex-1">
            <PerformerPicker
              categoryGuid={categoryGuid}
              value={selectedPerformer}
              onChange={setSelectedPerformer}
              excludeGuids={addedPerformerGuids}
              placeholder="Select performer to add..."
            />
          </div>
          <Button
            size="sm"
            onClick={handleAddPerformer}
            disabled={!selectedPerformer || addLoading}
          >
            {addLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancelAdd}
            disabled={addLoading}
          >
            Cancel
          </Button>
        </div>
      )}

      {/* Performer List */}
      {performers.length === 0 && !isAddingPerformer ? (
        <div className="text-sm text-muted-foreground py-2">
          No performers assigned
        </div>
      ) : (
        <div className="space-y-2">
          {performers.map((performer) => (
            <div
              key={performer.guid}
              className="flex items-center justify-between gap-2 p-2 rounded-md bg-muted/50"
            >
              {/* Performer Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{performer.name}</div>
                {performer.instagram_handle && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Instagram className="h-3 w-3" />
                    <span>@{performer.instagram_handle}</span>
                  </div>
                )}
              </div>

              {/* Status & Actions */}
              <div className="flex items-center gap-2">
                {editable ? (
                  <>
                    {/* Status Dropdown */}
                    <Select
                      value={performer.status}
                      onValueChange={(value) => handleStatusChange(performer.guid, value as PerformerStatus)}
                      disabled={statusLoading === performer.guid}
                    >
                      <SelectTrigger className="h-7 w-[120px]">
                        {statusLoading === performer.guid ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <SelectValue />
                        )}
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="announced">
                          <span className="flex items-center gap-1">
                            <Megaphone className="h-3 w-3 text-blue-600" />
                            Announced
                          </span>
                        </SelectItem>
                        <SelectItem value="confirmed">
                          <span className="flex items-center gap-1">
                            <Check className="h-3 w-3 text-green-600" />
                            Confirmed
                          </span>
                        </SelectItem>
                        <SelectItem value="cancelled">
                          <span className="flex items-center gap-1">
                            <Ban className="h-3 w-3 text-red-600" />
                            Cancelled
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>

                    {/* Remove Button */}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => setRemovePerformer(performer)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </>
                ) : (
                  <PerformerStatusBadge status={performer.status} />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Remove Confirmation Dialog */}
      <AlertDialog
        open={removePerformer !== null}
        onOpenChange={(open) => !open && setRemovePerformer(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Performer</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove "{removePerformer?.name}" from this event?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={removeLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemovePerformer}
              disabled={removeLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {removeLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default EventPerformersSection
