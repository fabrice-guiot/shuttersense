/**
 * Connectors Page
 *
 * Manage remote storage connectors with CRUD operations
 */

import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useConnectors } from '../hooks/useConnectors'
import { ConnectorList } from '../components/connectors/ConnectorList'
import ConnectorForm from '../components/connectors/ConnectorForm'
import type { Connector } from '@/contracts/api/connector-api'

export default function ConnectorsPage() {
  const {
    connectors,
    loading,
    error,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector
  } = useConnectors()

  const [open, setOpen] = useState(false)
  const [editingConnector, setEditingConnector] = useState<Connector | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (connector: Connector | null = null) => {
    setEditingConnector(connector)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingConnector(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingConnector) {
        await updateConnector(editingConnector.id, formData)
      } else {
        await createConnector(formData)
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (connector: Connector) => {
    deleteConnector(connector.id).catch(() => {
      // Error handled by hook
    })
  }

  const handleTest = (connector: Connector) => {
    testConnector(connector.id).catch(() => {
      // Error handled by hook
    })
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Remote Storage Connectors</h1>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Connector
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Connector List */}
      <ConnectorList
        connectors={connectors}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
        onTest={handleTest}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingConnector ? 'Edit Connector' : 'New Connector'}
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <ConnectorForm
              connector={editingConnector}
              onSubmit={handleSubmit}
              onCancel={handleClose}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
