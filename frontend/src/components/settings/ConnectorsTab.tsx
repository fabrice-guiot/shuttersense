/**
 * Connectors Tab Component
 *
 * Manage remote storage connectors with CRUD operations.
 * Extracted from ConnectorsPage for use within SettingsPage tabs.
 */

import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useConnectors, useConnectorStats } from '@/hooks/useConnectors'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { ConnectorList } from '@/components/connectors/ConnectorList'
import ConnectorForm from '@/components/connectors/ConnectorForm'
import { GuidBadge } from '@/components/GuidBadge'
import type { Connector } from '@/contracts/api/connector-api'

export function ConnectorsTab() {
  const {
    connectors,
    loading,
    error,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector
  } = useConnectors()

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useConnectorStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Active Connectors', value: stats.active_connectors },
        { label: 'Total Connectors', value: stats.total_connectors },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

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
        await updateConnector(editingConnector.guid, formData)
      } else {
        await createConnector(formData)
        // Refresh KPI stats after creating a new connector
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (connector: Connector) => {
    deleteConnector(connector.guid)
      .then(() => {
        // Refresh KPI stats after deleting a connector
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  const handleTest = async (connector: Connector) => {
    try {
      const result = await testConnector(connector.guid)
      if (result.success) {
        toast.success('Connection successful', {
          description: result.message
        })
      } else {
        toast.error('Connection failed', {
          description: result.message
        })
      }
    } catch (err: any) {
      toast.error('Connection test failed', {
        description: err.message || 'An unexpected error occurred'
      })
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row (Issue #67 - Single Title Pattern) */}
      <div className="flex justify-end">
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
        <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>
              {editingConnector ? 'Edit Connector' : 'New Connector'}
            </DialogTitle>
            {editingConnector && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingConnector.guid} />
                </div>
              </DialogDescription>
            )}
          </DialogHeader>
          <div className="mt-4 overflow-y-auto flex-1 pr-2">
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

export default ConnectorsTab
