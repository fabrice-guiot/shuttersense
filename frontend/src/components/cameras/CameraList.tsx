/**
 * CameraList component
 *
 * Displays a table of cameras with status badges, audit info, and edit/delete actions.
 * Uses ResponsiveTable for mobile-friendly display.
 */

import { useState } from 'react'
import { Camera, Edit, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Badge } from '@/components/ui/badge'
import { AuditTrailPopover } from '@/components/audit'
import type { CameraResponse } from '@/contracts/api/camera-api'

// ============================================================================
// Types
// ============================================================================

interface CameraListProps {
  cameras: CameraResponse[]
  loading: boolean
  onEdit: (camera: CameraResponse) => void
  onDelete: (camera: CameraResponse) => void
}

// ============================================================================
// Component
// ============================================================================

export function CameraList({ cameras, loading, onEdit, onDelete }: CameraListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    camera: CameraResponse | null
  }>({ open: false, camera: null })

  const handleDeleteClick = (camera: CameraResponse) => {
    setDeleteDialog({ open: true, camera })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.camera) {
      onDelete(deleteDialog.camera)
      setDeleteDialog({ open: false, camera: null })
    }
  }

  if (loading && cameras.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading cameras...</div>
      </div>
    )
  }

  if (cameras.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Camera className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <div className="text-muted-foreground mb-2">No cameras found</div>
        <p className="text-sm text-muted-foreground">
          Cameras are automatically discovered when agents analyze photo collections
        </p>
      </div>
    )
  }

  const cameraColumns: ColumnDef<CameraResponse>[] = [
    {
      header: 'Camera ID',
      cell: (camera) => (
        <span className="font-mono text-sm">{camera.camera_id}</span>
      ),
      cellClassName: 'font-medium',
      cardRole: 'title',
    },
    {
      header: 'Display Name',
      cell: (camera) => camera.display_name || (
        <span className="text-muted-foreground">\u2014</span>
      ),
      cardRole: 'subtitle',
    },
    {
      header: 'Make',
      cell: (camera) => camera.make || (
        <span className="text-muted-foreground">\u2014</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Model',
      cell: (camera) => camera.model || (
        <span className="text-muted-foreground">\u2014</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Status',
      cell: (camera) => (
        <Badge variant={camera.status === 'confirmed' ? 'default' : 'secondary'}>
          {camera.status === 'confirmed' ? 'Confirmed' : 'Temporary'}
        </Badge>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Modified',
      cell: (camera) => (
        <AuditTrailPopover audit={camera.audit} fallbackTimestamp={camera.updated_at} />
      ),
      cellClassName: 'text-muted-foreground',
      cardRole: 'hidden',
    },
    {
      header: 'Actions',
      headerClassName: 'text-right',
      cell: (camera) => (
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onEdit(camera)}
            title="Edit camera"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleDeleteClick(camera)}
            title="Delete camera"
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
      cardRole: 'action',
    },
  ]

  return (
    <>
      <ResponsiveTable
        data={cameras}
        columns={cameraColumns}
        keyField="guid"
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) => {
          if (!open) setDeleteDialog({ open: false, camera: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Camera</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete camera "{deleteDialog.camera?.camera_id}"
              {deleteDialog.camera?.display_name && ` (${deleteDialog.camera.display_name})`}?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, camera: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default CameraList
