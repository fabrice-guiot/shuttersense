/**
 * CameraEditDialog component
 *
 * Dialog for updating camera details: status, display_name, make, model, serial_number, notes.
 */

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { GuidBadge } from '@/components/GuidBadge'
import type { CameraResponse, CameraUpdateRequest, CameraStatus } from '@/contracts/api/camera-api'

// ============================================================================
// Types
// ============================================================================

interface CameraEditDialogProps {
  camera: CameraResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (guid: string, data: CameraUpdateRequest) => Promise<void>
}

// ============================================================================
// Component
// ============================================================================

export function CameraEditDialog({ camera, open, onOpenChange, onSubmit }: CameraEditDialogProps) {
  const [status, setStatus] = useState<CameraStatus>('temporary')
  const [displayName, setDisplayName] = useState('')
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [serialNumber, setSerialNumber] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset form when camera changes
  useEffect(() => {
    if (camera) {
      setStatus(camera.status)
      setDisplayName(camera.display_name || '')
      setMake(camera.make || '')
      setModel(camera.model || '')
      setSerialNumber(camera.serial_number || '')
      setNotes(camera.notes || '')
      setError(null)
    }
  }, [camera])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!camera) return

    setSaving(true)
    setError(null)
    try {
      await onSubmit(camera.guid, {
        status,
        display_name: displayName || undefined,
        make: make || undefined,
        model: model || undefined,
        serial_number: serialNumber || undefined,
        notes: notes || undefined,
      })
      onOpenChange(false)
    } catch (err: any) {
      setError(err.userMessage || 'Failed to update camera')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Edit Camera</DialogTitle>
          {camera && (
            <DialogDescription asChild>
              <div className="pt-1 flex items-center gap-2">
                <span className="font-mono">{camera.camera_id}</span>
                <GuidBadge guid={camera.guid} />
              </div>
            </DialogDescription>
          )}
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto mt-4 pr-2">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-4">
            <div className="space-y-2">
              <Label htmlFor="cam-status">Status</Label>
              <Select value={status} onValueChange={(v) => setStatus(v as CameraStatus)}>
                <SelectTrigger id="cam-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="temporary">Temporary</SelectItem>
                  <SelectItem value="confirmed">Confirmed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cam-display-name">Display Name</Label>
              <Input
                id="cam-display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Canon EOS R5"
                maxLength={100}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="cam-make">Make</Label>
                <Input
                  id="cam-make"
                  value={make}
                  onChange={(e) => setMake(e.target.value)}
                  placeholder="e.g. Canon"
                  maxLength={100}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cam-model">Model</Label>
                <Input
                  id="cam-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="e.g. EOS R5"
                  maxLength={100}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cam-serial">Serial Number</Label>
              <Input
                id="cam-serial"
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                placeholder="e.g. 12345678"
                maxLength={100}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cam-notes">Notes</Label>
              <Textarea
                id="cam-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional notes about this camera"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default CameraEditDialog
