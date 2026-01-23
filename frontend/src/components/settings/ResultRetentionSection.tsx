/**
 * Result Retention Section Component
 *
 * Manages retention policy configuration for jobs and analysis results.
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { useState } from 'react'
import { Archive, Pencil, Loader2 } from 'lucide-react'
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
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import type {
  RetentionSettingsResponse,
  RetentionSettingsUpdate,
  RetentionDays,
  PreserveCount
} from '@/contracts/api/retention-api'
import {
  RETENTION_LABELS,
  PRESERVE_LABELS
} from '@/contracts/api/retention-api'

// ============================================================================
// Types
// ============================================================================

interface ResultRetentionSectionProps {
  /** Current retention settings */
  settings: RetentionSettingsResponse | null
  /** Loading state */
  loading?: boolean
  /** Called when settings are updated */
  onUpdate: (update: RetentionSettingsUpdate) => Promise<void>
}

type SettingKey = keyof RetentionSettingsResponse

interface SettingConfig {
  key: SettingKey
  label: string
  description: string
  type: 'retention' | 'preserve'
}

// ============================================================================
// Constants
// ============================================================================

const SETTINGS_CONFIG: SettingConfig[] = [
  {
    key: 'job_completed_days',
    label: 'Completed Jobs',
    description: 'How long to keep completed job records',
    type: 'retention'
  },
  {
    key: 'job_failed_days',
    label: 'Failed Jobs',
    description: 'How long to keep failed job records and their results',
    type: 'retention'
  },
  {
    key: 'result_completed_days',
    label: 'Completed Results',
    description: 'How long to keep completed analysis results (0 = unlimited)',
    type: 'retention'
  },
  {
    key: 'preserve_per_collection',
    label: 'Preserved Results',
    description: 'Minimum results to keep per collection+tool (regardless of age)',
    type: 'preserve'
  }
]

const RETENTION_OPTIONS: RetentionDays[] = [0, 1, 2, 5, 7, 14, 30, 90, 180, 365]
const PRESERVE_OPTIONS: PreserveCount[] = [1, 2, 3, 5, 10]

// ============================================================================
// Helper Functions
// ============================================================================

function formatRetentionValue(value: number, type: 'retention' | 'preserve'): string {
  if (type === 'preserve') {
    return PRESERVE_LABELS[value as PreserveCount] || `${value} results`
  }
  return RETENTION_LABELS[value as RetentionDays] || `${value} days`
}

// ============================================================================
// Component
// ============================================================================

export function ResultRetentionSection({
  settings,
  loading = false,
  onUpdate
}: ResultRetentionSectionProps) {
  // Dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Edit form state
  const [editingConfig, setEditingConfig] = useState<SettingConfig | null>(null)
  const [selectedValue, setSelectedValue] = useState<string>('')

  // Open edit dialog
  const handleEdit = (config: SettingConfig) => {
    const currentValue = settings?.[config.key] ?? 0
    setEditingConfig(config)
    setSelectedValue(String(currentValue))
    setFormError(null)
    setEditDialogOpen(true)
  }

  // Handle save
  const handleSave = async () => {
    if (!editingConfig) return

    const value = parseInt(selectedValue, 10)
    if (isNaN(value)) {
      setFormError('Invalid value selected')
      return
    }

    setIsSubmitting(true)
    setFormError(null)

    try {
      const update: RetentionSettingsUpdate = {
        [editingConfig.key]: value
      }
      await onUpdate(update)
      setEditDialogOpen(false)
    } catch (err: any) {
      setFormError(err.message || 'Update failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Archive className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle className="text-lg">Result Retention Policy</CardTitle>
            <CardDescription>
              Configure automatic cleanup of old jobs and analysis results
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
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
          </div>
        ) : !settings ? (
          <p className="text-sm text-muted-foreground">
            Unable to load retention settings
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Setting</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Value</TableHead>
                <TableHead className="w-16">Edit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {SETTINGS_CONFIG.map((config) => (
                <TableRow key={config.key}>
                  <TableCell className="font-medium">
                    {config.label}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {config.description}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono">
                      {formatRetentionValue(settings[config.key], config.type)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(config)}
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
              Edit {editingConfig?.label}
            </DialogTitle>
            <DialogDescription>
              {editingConfig?.description}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="retentionValue">
                {editingConfig?.type === 'preserve' ? 'Results to Keep' : 'Retention Period'}
              </Label>
              <Select
                value={selectedValue}
                onValueChange={setSelectedValue}
              >
                <SelectTrigger id="retentionValue">
                  <SelectValue placeholder="Select value" />
                </SelectTrigger>
                <SelectContent>
                  {editingConfig?.type === 'preserve' ? (
                    PRESERVE_OPTIONS.map((value) => (
                      <SelectItem key={value} value={String(value)}>
                        {PRESERVE_LABELS[value]}
                      </SelectItem>
                    ))
                  ) : (
                    RETENTION_OPTIONS.map((value) => (
                      <SelectItem key={value} value={String(value)}>
                        {RETENTION_LABELS[value]}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              {editingConfig?.type === 'retention' && (
                <p className="text-xs text-muted-foreground">
                  Select "Unlimited" to disable automatic cleanup for this category.
                </p>
              )}
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

export default ResultRetentionSection
