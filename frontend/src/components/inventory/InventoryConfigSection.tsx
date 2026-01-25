/**
 * InventoryConfigSection Component
 *
 * Complete inventory configuration section for a connector.
 * Combines status display, configuration form, and action buttons.
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { useState } from 'react'
import { Settings, Trash2, Play, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import { InventoryConfigForm } from './InventoryConfigForm'
import { InventoryStatusDisplay } from './InventoryStatusDisplay'
import { useInventoryConfig, useInventoryStatus, useInventoryImport } from '@/hooks/useInventory'
import type { Connector } from '@/contracts/api/connector-api'
import type { InventoryConfig, InventorySchedule } from '@/contracts/api/inventory-api'

// ============================================================================
// Component Props
// ============================================================================

export interface InventoryConfigSectionProps {
  /** Connector to configure inventory for */
  connector: Connector
  /** Callback when configuration changes */
  onConfigChange?: () => void
  /** Additional CSS class */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function InventoryConfigSection({
  connector,
  onConfigChange,
  className
}: InventoryConfigSectionProps) {
  const [configDialogOpen, setConfigDialogOpen] = useState(false)
  const [clearDialogOpen, setClearDialogOpen] = useState(false)

  const { setConfig, clearConfig, loading: configLoading, error: configError } = useInventoryConfig()
  const { status, loading: statusLoading, refetch: refetchStatus } = useInventoryStatus(connector.guid, {
    pollInterval: 5000,
    autoFetch: true
  })
  const { triggerImport, loading: importLoading } = useInventoryImport()

  // Only S3 and GCS connectors support inventory
  const supportsInventory = connector.type === 's3' || connector.type === 'gcs'

  if (!supportsInventory) {
    return (
      <div className={className}>
        <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          Inventory import is only available for S3 and GCS connectors.
        </div>
      </div>
    )
  }

  // Determine if config exists (we check validation_status as proxy)
  const hasConfig = status?.validation_status !== null

  const handleSaveConfig = async (config: InventoryConfig, schedule: InventorySchedule) => {
    await setConfig(connector.guid, config, schedule)
    setConfigDialogOpen(false)
    refetchStatus()
    onConfigChange?.()
  }

  const handleClearConfig = async () => {
    await clearConfig(connector.guid)
    setClearDialogOpen(false)
    refetchStatus()
    onConfigChange?.()
  }

  const handleTriggerImport = async () => {
    await triggerImport(connector.guid)
    refetchStatus()
  }

  const canTriggerImport =
    status?.validation_status === 'validated' &&
    !status?.current_job

  return (
    <div className={className}>
      <div className="space-y-4">
        {/* Header with Actions */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Bucket Inventory</h3>
          <div className="flex items-center gap-2">
            {hasConfig && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchStatus()}
                  disabled={statusLoading}
                  className="gap-1"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setClearDialogOpen(true)}
                  disabled={configLoading}
                  className="gap-1 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfigDialogOpen(true)}
              className="gap-1"
            >
              <Settings className="h-3.5 w-3.5" />
              {hasConfig ? 'Edit' : 'Configure'}
            </Button>
          </div>
        </div>

        {/* Status Display */}
        <InventoryStatusDisplay status={status} loading={statusLoading} />

        {/* Import Action */}
        {hasConfig && (
          <div className="flex justify-start">
            <Button
              onClick={handleTriggerImport}
              disabled={!canTriggerImport || importLoading}
              className="gap-2"
            >
              <Play className="h-4 w-4" />
              {importLoading ? 'Starting...' : 'Import Now'}
            </Button>
            {!canTriggerImport && status?.validation_status !== 'validated' && (
              <span className="ml-3 self-center text-sm text-muted-foreground">
                Validation required before import
              </span>
            )}
            {status?.current_job && (
              <span className="ml-3 self-center text-sm text-muted-foreground">
                Import in progress...
              </span>
            )}
          </div>
        )}
      </div>

      {/* Configure Dialog */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {hasConfig ? 'Edit Inventory Configuration' : 'Configure Bucket Inventory'}
            </DialogTitle>
            <DialogDescription>
              {connector.type === 's3'
                ? 'Configure S3 Inventory to import file metadata from your bucket.'
                : 'Configure GCS Storage Insights to import file metadata from your bucket.'}
            </DialogDescription>
          </DialogHeader>
          <InventoryConfigForm
            connectorType={connector.type}
            existingConfig={
              status?.validation_status
                ? {
                    provider: connector.type === 'gcs' ? 'gcs' : 's3',
                    // Note: We don't have the full config in status, this is a limitation
                    // The form will show empty fields for edit - user must re-enter
                  } as InventoryConfig
                : null
            }
            existingSchedule="manual"
            onSubmit={handleSaveConfig}
            onCancel={() => setConfigDialogOpen(false)}
            loading={configLoading}
            error={configError}
          />
        </DialogContent>
      </Dialog>

      {/* Clear Confirmation Dialog */}
      <AlertDialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Inventory Configuration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove the inventory configuration?
              This will also delete all discovered folders. Collections created from
              inventory folders will not be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClearConfig}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default InventoryConfigSection
