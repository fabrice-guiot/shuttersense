/**
 * Configuration Page
 *
 * Manage application configuration including cameras, extensions, and processing methods.
 * Supports YAML import/export and conflict resolution.
 */

import { useState, useEffect, useRef } from 'react'
import { Upload, Download, Settings, Camera, FileCode, Cog, Plus, Trash2, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useConfig, useConfigStats } from '../hooks/useConfig'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import type {
  ConfigCategory,
  ImportSessionResponse
} from '@/contracts/api/config-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Conflict Value Display Helpers
// ============================================================================

/**
 * Flatten an object/array into dot-notation paths with values
 * e.g., { name: "Canon", serial: "123" } => [["name", "Canon"], ["serial", "123"]]
 *
 * Single-element arrays are unwrapped to avoid [0]. prefix noise
 */
function flattenValue(value: unknown, prefix = ''): Array<[string, string]> {
  const results: Array<[string, string]> = []

  if (value === null || value === undefined) {
    results.push([prefix || '(value)', 'null'])
  } else if (Array.isArray(value)) {
    if (value.length === 0) {
      results.push([prefix || '(value)', '[]'])
    } else if (value.length === 1 && typeof value[0] === 'object' && value[0] !== null) {
      // Single-element array with object: unwrap it (avoid [0]. prefix)
      results.push(...flattenValue(value[0], prefix))
    } else {
      value.forEach((item, index) => {
        const path = prefix ? `${prefix}[${index}]` : `[${index}]`
        if (typeof item === 'object' && item !== null) {
          results.push(...flattenValue(item, path))
        } else {
          results.push([path, String(item)])
        }
      })
    }
  } else if (typeof value === 'object') {
    const entries = Object.entries(value)
    if (entries.length === 0) {
      results.push([prefix || '(value)', '{}'])
    } else {
      entries.forEach(([key, val]) => {
        const path = prefix ? `${prefix}.${key}` : key
        if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
          results.push(...flattenValue(val, path))
        } else if (Array.isArray(val)) {
          results.push(...flattenValue(val, path))
        } else {
          results.push([path, String(val)])
        }
      })
    }
  } else {
    results.push([prefix || '(value)', String(value)])
  }

  return results
}

/**
 * Get all unique paths from two flattened value lists, in consistent order
 */
function getAllPaths(flat1: Array<[string, string]>, flat2: Array<[string, string]>): string[] {
  const pathSet = new Set<string>()
  flat1.forEach(([path]) => pathSet.add(path))
  flat2.forEach(([path]) => pathSet.add(path))
  return Array.from(pathSet).sort()
}

/**
 * Build a map from path to value for quick lookup
 */
function buildPathMap(flat: Array<[string, string]>): Map<string, string> {
  return new Map(flat)
}

interface ConflictValueDisplayProps {
  currentValue: unknown
  newValue: unknown
  side: 'current' | 'new'
}

/**
 * Display a value with dot-notation paths, highlighting differences
 */
function ConflictValueDisplay({ currentValue, newValue, side }: ConflictValueDisplayProps) {
  const currentFlat = flattenValue(currentValue)
  const newFlat = flattenValue(newValue)
  const allPaths = getAllPaths(currentFlat, newFlat)
  const currentMap = buildPathMap(currentFlat)
  const newMap = buildPathMap(newFlat)

  const displayMap = side === 'current' ? currentMap : newMap
  const compareMap = side === 'current' ? newMap : currentMap

  return (
    <div className="text-xs font-mono space-y-0.5">
      {allPaths.map(path => {
        const value = displayMap.get(path)
        const otherValue = compareMap.get(path)
        const isDifferent = value !== otherValue
        const isMissing = value === undefined

        if (isMissing) {
          return (
            <div key={path} className="text-muted-foreground/50 line-through">
              <span className="text-muted-foreground">{path}:</span> {otherValue}
            </div>
          )
        }

        return (
          <div
            key={path}
            className={cn(
              isDifferent && 'bg-yellow-100 dark:bg-yellow-900/30 -mx-1 px-1 rounded'
            )}
          >
            <span className="text-muted-foreground">{path}:</span>{' '}
            <span className={cn(isDifferent && 'font-medium')}>{value}</span>
          </div>
        )
      })}
    </div>
  )
}

/**
 * Simple value display using dot-notation (without comparison)
 */
function ValueDisplay({ value }: { value: unknown }) {
  const flat = flattenValue(value)

  return (
    <div className="text-sm font-mono space-y-0.5">
      {flat.map(([path, val]) => (
        <div key={path}>
          <span className="text-muted-foreground">{path}:</span> {val}
        </div>
      ))}
    </div>
  )
}

/**
 * Extract a property from a value, handling arrays (first element) and objects
 */
function extractProperty(value: unknown, property: string): string {
  if (value === null || value === undefined) return ''

  // If it's an array, use the first element
  const target = Array.isArray(value) ? value[0] : value

  if (typeof target === 'object' && target !== null) {
    const propValue = (target as Record<string, unknown>)[property]
    return propValue !== undefined && propValue !== null ? String(propValue) : ''
  }

  // For simple values (like processing_methods strings)
  if (property === 'value' || property === 'description') {
    return typeof value === 'string' ? value : ''
  }

  return ''
}

// Category icons and labels
const CATEGORY_CONFIG = {
  cameras: {
    icon: Camera,
    label: 'Camera Mappings',
    description: 'Map camera IDs to camera names and serial numbers'
  },
  processing_methods: {
    icon: Cog,
    label: 'Processing Methods',
    description: 'Define processing method codes and descriptions'
  },
  extensions: {
    icon: FileCode,
    label: 'File Extensions',
    description: 'Configure photo and metadata file extensions'
  }
} as const

export default function ConfigurationPage() {
  const {
    configuration,
    loading,
    error,
    fetchConfiguration,
    createConfigValue,
    updateConfigValue,
    deleteConfigValue,
    startImport,
    resolveImport,
    cancelImport,
    exportConfiguration
  } = useConfig()

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useConfigStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Cameras', value: stats.cameras_configured },
        { label: 'Methods', value: stats.processing_methods_configured },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  // Dialog states
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<{
    category: ConfigCategory
    key: string
    value: unknown
  } | null>(null)
  const [deletingItem, setDeletingItem] = useState<{
    category: ConfigCategory
    key: string
  } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  // Import state
  const [importSession, setImportSession] = useState<ImportSessionResponse | null>(null)
  const [importLoading, setImportLoading] = useState(false)
  const [conflictResolutions, setConflictResolutions] = useState<Map<string, boolean>>(new Map())
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Camera entry type for array editing
  interface CameraEntry {
    name: string
    serial_number: string
  }

  // Edit form state
  const [editFormData, setEditFormData] = useState<{
    cameraId?: string
    cameras?: CameraEntry[]  // For camera array editing
    description?: string
    value?: string
    extensions?: string[]  // For extension array editing
  }>({})

  // New extension input state
  const [newExtensionInput, setNewExtensionInput] = useState('')

  // New camera entry state
  const [newCameraEntry, setNewCameraEntry] = useState<CameraEntry>({ name: '', serial_number: '' })

  // Handle import file selection
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setImportLoading(true)
    setFormError(null)
    try {
      const session = await startImport(file)
      setImportSession(session)

      // Initialize conflict resolutions (default to use_yaml)
      const resolutions = new Map<string, boolean>()
      session.conflicts.forEach(conflict => {
        resolutions.set(`${conflict.category}:${conflict.key}`, true)
      })
      setConflictResolutions(resolutions)

      setImportDialogOpen(true)
    } catch (err: any) {
      setFormError(err.userMessage || 'Failed to import file')
    } finally {
      setImportLoading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // Handle import confirmation
  const handleImportConfirm = async () => {
    if (!importSession) return

    setImportLoading(true)
    try {
      const resolutions = Array.from(conflictResolutions.entries()).map(([key, useYaml]) => {
        const [category, configKey] = key.split(':')
        return {
          category: category as ConfigCategory,
          key: configKey,
          use_yaml: useYaml
        }
      })

      await resolveImport(importSession.session_id, { resolutions })
      setImportDialogOpen(false)
      setImportSession(null)
      refetchStats()
    } catch (err: any) {
      setFormError(err.userMessage || 'Failed to apply import')
    } finally {
      setImportLoading(false)
    }
  }

  // Handle import cancel
  const handleImportCancel = async () => {
    if (importSession) {
      await cancelImport(importSession.session_id)
    }
    setImportDialogOpen(false)
    setImportSession(null)
    setConflictResolutions(new Map())
  }

  // Handle export
  const handleExport = async () => {
    await exportConfiguration()
  }

  // Open edit dialog
  const handleEdit = (category: ConfigCategory, key: string, value: unknown) => {
    setEditingItem({ category, key, value })

    // Initialize form data based on category
    if (category === 'cameras') {
      // Cameras can be an array or a single object - normalize to array
      let cameraArray: CameraEntry[] = []
      if (Array.isArray(value)) {
        cameraArray = value.map(v => ({
          name: v?.name || '',
          serial_number: v?.serial_number || ''
        }))
      } else if (value && typeof value === 'object') {
        cameraArray = [{
          name: (value as any).name || '',
          serial_number: (value as any).serial_number || ''
        }]
      }
      setEditFormData({ cameras: cameraArray })
      setNewCameraEntry({ name: '', serial_number: '' })
    } else if (category === 'processing_methods') {
      // Processing methods can be a string or an object with description
      const desc = typeof value === 'string' ? value : extractProperty(value, 'description')
      setEditFormData({
        description: desc
      })
    } else if (category === 'extensions') {
      // Extensions are arrays of strings
      const extArray = Array.isArray(value) ? [...value] : []
      setEditFormData({
        extensions: extArray
      })
      setNewExtensionInput('')
    }

    setFormError(null)
    setEditDialogOpen(true)
  }

  // Open add dialog
  const handleAdd = (category: ConfigCategory) => {
    setEditingItem({ category, key: '', value: null })
    if (category === 'cameras') {
      setEditFormData({ cameras: [] })
      setNewCameraEntry({ name: '', serial_number: '' })
    } else {
      setEditFormData({})
    }
    setFormError(null)
    setEditDialogOpen(true)
  }

  // Get current photo_extensions for require_sidecar validation
  const getPhotoExtensions = (): string[] => {
    if (!configuration?.extensions?.photo_extensions) return []
    return Array.isArray(configuration.extensions.photo_extensions)
      ? configuration.extensions.photo_extensions
      : []
  }

  // Handle edit save
  const handleEditSave = async () => {
    if (!editingItem) return

    setFormError(null)
    try {
      let value: unknown

      if (editingItem.category === 'cameras') {
        // Cameras are saved as an array
        const cameras = editFormData.cameras || []
        if (cameras.length === 0) {
          setFormError('At least one camera entry is required')
          return
        }
        value = cameras
      } else if (editingItem.category === 'processing_methods') {
        value = editFormData.description || ''
      } else if (editingItem.category === 'extensions') {
        value = editFormData.extensions || []

        // Validate require_sidecar against photo_extensions
        if (editingItem.key === 'require_sidecar') {
          const photoExts = getPhotoExtensions()
          const invalidExts = (editFormData.extensions || []).filter(
            ext => !photoExts.includes(ext)
          )
          if (invalidExts.length > 0) {
            setFormError(
              `Invalid extensions for require_sidecar: ${invalidExts.join(', ')}. ` +
              `Only extensions from photo_extensions are allowed.`
            )
            return
          }
        }
      } else {
        value = editFormData.value
      }

      // Determine the key: use existing key for edits, or appropriate field for new items
      let key = editingItem.key
      if (!key) {
        if (editingItem.category === 'cameras') {
          key = editFormData.cameraId || ''
          if (!key) {
            setFormError('Camera ID is required')
            return
          }
        } else if (editingItem.category === 'processing_methods') {
          key = editFormData.value || ''
        } else {
          key = ''
        }
      }

      if (editingItem.value === null) {
        // Creating new
        await createConfigValue(editingItem.category, key, { value })
      } else {
        // Updating existing
        await updateConfigValue(editingItem.category, editingItem.key, { value })
      }

      setEditDialogOpen(false)
      setEditingItem(null)
      refetchStats()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  // Open delete confirmation
  const handleDeleteClick = (category: ConfigCategory, key: string) => {
    setDeletingItem({ category, key })
    setDeleteDialogOpen(true)
  }

  // Handle delete confirm
  const handleDeleteConfirm = async () => {
    if (!deletingItem) return

    try {
      await deleteConfigValue(deletingItem.category, deletingItem.key)
      setDeleteDialogOpen(false)
      setDeletingItem(null)
      refetchStats()
    } catch (err: any) {
      setFormError(err.userMessage || 'Delete failed')
    }
  }

  // Render category section
  const renderCategorySection = (category: ConfigCategory) => {
    const config = CATEGORY_CONFIG[category]
    const Icon = config.icon

    let items: Array<{ key: string; value: unknown }> = []

    if (configuration) {
      if (category === 'cameras') {
        items = Object.entries(configuration.cameras).map(([key, value]) => ({
          key,
          value
        }))
      } else if (category === 'processing_methods') {
        items = Object.entries(configuration.processing_methods).map(([key, value]) => ({
          key,
          value
        }))
      } else if (category === 'extensions') {
        // For extensions, show as key-value pairs
        const ext = configuration.extensions
        // Always show all extension keys (even if empty) so they can be edited
        items.push({ key: 'photo_extensions', value: ext.photo_extensions || [] })
        items.push({ key: 'metadata_extensions', value: ext.metadata_extensions || [] })
        items.push({ key: 'require_sidecar', value: ext.require_sidecar || [] })
      }
    }

    return (
      <Card key={category}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
            <div>
              <CardTitle className="text-lg">{config.label}</CardTitle>
              <CardDescription>{config.description}</CardDescription>
            </div>
          </div>
          {category !== 'extensions' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAdd(category)}
              className="gap-1"
            >
              <Plus className="h-4 w-4" />
              Add
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              <div className="h-8 w-full bg-muted animate-pulse rounded" />
              <div className="h-8 w-full bg-muted animate-pulse rounded" />
            </div>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No items configured</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead className="w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map(item => (
                  <TableRow key={item.key}>
                    <TableCell className="font-mono">{item.key}</TableCell>
                    <TableCell>
                      {category === 'extensions' ? (
                        <div className="flex flex-wrap gap-1">
                          {Array.isArray(item.value) && (item.value as string[]).length > 0 ? (
                            (item.value as string[]).map(ext => (
                              <Badge key={ext} variant="secondary">{ext}</Badge>
                            ))
                          ) : (
                            <span className="text-muted-foreground italic">Empty</span>
                          )}
                        </div>
                      ) : category === 'cameras' ? (
                        <div className="space-y-1">
                          {(() => {
                            // Normalize camera value to array
                            const cameras = Array.isArray(item.value)
                              ? item.value
                              : item.value ? [item.value] : []
                            if (cameras.length === 0) {
                              return <span className="text-muted-foreground italic">Empty</span>
                            }
                            return cameras.map((cam: any, idx: number) => (
                              <div key={idx} className="text-sm">
                                {cam.name || 'Unnamed'}
                                {cam.serial_number && (
                                  <span className="text-muted-foreground ml-1">
                                    (SN: {cam.serial_number})
                                  </span>
                                )}
                              </div>
                            ))
                          })()}
                        </div>
                      ) : typeof item.value === 'string' ? (
                        <span>{item.value}</span>
                      ) : (
                        <ValueDisplay value={item.value} />
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(category, item.key, item.value)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        {category !== 'extensions' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteClick(category, item.key)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="h-8 w-8" />
          <h1 className="text-3xl font-bold tracking-tight">Configuration</h1>
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".yaml,.yml"
            className="hidden"
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={importLoading}
            className="gap-2"
          >
            <Upload className="h-4 w-4" />
            Import YAML
          </Button>
          <Button
            variant="outline"
            onClick={handleExport}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Export YAML
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Category Sections */}
      <div className="grid gap-6">
        {renderCategorySection('cameras')}
        {renderCategorySection('processing_methods')}
        {renderCategorySection('extensions')}
      </div>

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={handleImportCancel}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Configuration</DialogTitle>
            <DialogDescription>
              {importSession?.file_name && `File: ${importSession.file_name}`}
            </DialogDescription>
          </DialogHeader>

          {importSession && (
            <div className="space-y-4">
              {/* Import Summary */}
              <div className="flex gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Total items: </span>
                  <span className="font-medium">{importSession.total_items}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">New items: </span>
                  <span className="font-medium text-green-600">{importSession.new_items}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Conflicts: </span>
                  <span className="font-medium text-yellow-600">
                    {importSession.conflicts.length}
                  </span>
                </div>
              </div>

              {/* Conflicts */}
              {importSession.conflicts.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium">Resolve Conflicts</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Item</TableHead>
                        <TableHead>Current Value</TableHead>
                        <TableHead>New Value</TableHead>
                        <TableHead className="w-32">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {importSession.conflicts.map(conflict => {
                        const conflictKey = `${conflict.category}:${conflict.key}`
                        const useYaml = conflictResolutions.get(conflictKey) ?? true

                        return (
                          <TableRow key={conflictKey} className="align-top">
                            <TableCell>
                              <div className="font-mono text-sm">{conflict.key}</div>
                              <div className="text-xs text-muted-foreground">
                                {conflict.category}
                              </div>
                            </TableCell>
                            <TableCell className="max-w-56">
                              <ConflictValueDisplay
                                currentValue={conflict.database_value}
                                newValue={conflict.yaml_value}
                                side="current"
                              />
                            </TableCell>
                            <TableCell className="max-w-56">
                              <ConflictValueDisplay
                                currentValue={conflict.database_value}
                                newValue={conflict.yaml_value}
                                side="new"
                              />
                            </TableCell>
                            <TableCell>
                              <Button
                                variant={useYaml ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => {
                                  const newResolutions = new Map(conflictResolutions)
                                  newResolutions.set(conflictKey, !useYaml)
                                  setConflictResolutions(newResolutions)
                                }}
                              >
                                {useYaml ? 'Use New' : 'Keep Current'}
                              </Button>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}

              {formError && (
                <Alert variant="destructive">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={handleImportCancel}>
              Cancel
            </Button>
            <Button onClick={handleImportConfirm} disabled={importLoading}>
              {importLoading ? 'Importing...' : 'Apply Import'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={() => setEditDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingItem?.value === null ? 'Add' : 'Edit'}{' '}
              {editingItem?.category === 'cameras'
                ? 'Camera'
                : editingItem?.category === 'processing_methods'
                ? 'Processing Method'
                : 'Configuration'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {editingItem?.category === 'cameras' && (
              <div className="space-y-4">
                {/* Camera ID field for new cameras only */}
                {editingItem.value === null && (
                  <div className="space-y-2">
                    <Label htmlFor="cameraId">Camera ID</Label>
                    <Input
                      id="cameraId"
                      value={editFormData.cameraId || ''}
                      onChange={e => setEditFormData(prev => ({
                        ...prev,
                        cameraId: e.target.value.toUpperCase()
                      }))}
                      placeholder="e.g., AB3D"
                      maxLength={4}
                    />
                  </div>
                )}

                {/* Current camera entries */}
                <div className="space-y-2">
                  <Label>Camera Entries</Label>
                  <div className="space-y-2 p-2 border rounded-md bg-muted/30 min-h-[60px]">
                    {(editFormData.cameras || []).length === 0 ? (
                      <span className="text-sm text-muted-foreground italic">
                        No camera entries. Add at least one below.
                      </span>
                    ) : (
                      (editFormData.cameras || []).map((cam, idx) => (
                        <div key={idx} className="flex items-center gap-2 p-2 bg-background rounded border">
                          <div className="flex-1 text-sm">
                            <span className="font-medium">{cam.name || 'Unnamed'}</span>
                            {cam.serial_number && (
                              <span className="text-muted-foreground ml-2">
                                (SN: {cam.serial_number})
                              </span>
                            )}
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => {
                              setEditFormData(prev => ({
                                ...prev,
                                cameras: (prev.cameras || []).filter((_, i) => i !== idx)
                              }))
                            }}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Add new camera entry */}
                <div className="space-y-2 p-3 border rounded-md bg-muted/10">
                  <Label className="text-sm text-muted-foreground">Add Camera Entry</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      value={newCameraEntry.name}
                      onChange={e => setNewCameraEntry(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Camera Name"
                    />
                    <Input
                      value={newCameraEntry.serial_number}
                      onChange={e => setNewCameraEntry(prev => ({ ...prev, serial_number: e.target.value }))}
                      placeholder="Serial Number (optional)"
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      if (!newCameraEntry.name.trim()) {
                        setFormError('Camera name is required')
                        return
                      }
                      setEditFormData(prev => ({
                        ...prev,
                        cameras: [
                          ...(prev.cameras || []),
                          { name: newCameraEntry.name.trim(), serial_number: newCameraEntry.serial_number.trim() }
                        ]
                      }))
                      setNewCameraEntry({ name: '', serial_number: '' })
                      setFormError(null)
                    }}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Entry
                  </Button>
                </div>
              </div>
            )}

            {editingItem?.category === 'processing_methods' && (
              <>
                {editingItem.value === null && (
                  <div className="space-y-2">
                    <Label htmlFor="methodKey">Method Code</Label>
                    <Input
                      id="methodKey"
                      value={editFormData.value || ''}
                      onChange={e => setEditFormData(prev => ({
                        ...prev,
                        value: e.target.value
                      }))}
                      placeholder="e.g., HDR"
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="methodDescription">Description</Label>
                  <Input
                    id="methodDescription"
                    value={editFormData.description || ''}
                    onChange={e => setEditFormData(prev => ({
                      ...prev,
                      description: e.target.value
                    }))}
                    placeholder="e.g., High Dynamic Range"
                  />
                </div>
              </>
            )}

            {editingItem?.category === 'extensions' && (
              <div className="space-y-4">
                <Label>
                  {editingItem.key === 'photo_extensions' && 'Photo Extensions'}
                  {editingItem.key === 'metadata_extensions' && 'Metadata Extensions'}
                  {editingItem.key === 'require_sidecar' && 'Require Sidecar Extensions'}
                </Label>

                {/* Current extensions as removable badges */}
                <div className="flex flex-wrap gap-2 min-h-[32px] p-2 border rounded-md bg-muted/30">
                  {(editFormData.extensions || []).length === 0 ? (
                    <span className="text-sm text-muted-foreground italic">No extensions added</span>
                  ) : (
                    (editFormData.extensions || []).map(ext => (
                      <Badge key={ext} variant="secondary" className="gap-1 pr-1">
                        {ext}
                        <button
                          type="button"
                          className="ml-1 rounded-full hover:bg-muted p-0.5"
                          onClick={() => {
                            setEditFormData(prev => ({
                              ...prev,
                              extensions: (prev.extensions || []).filter(e => e !== ext)
                            }))
                          }}
                        >
                          <span className="sr-only">Remove {ext}</span>
                          <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
                            <path d="M3.05 3.05a.75.75 0 011.06 0L6 4.94l1.89-1.89a.75.75 0 111.06 1.06L7.06 6l1.89 1.89a.75.75 0 11-1.06 1.06L6 7.06 4.11 8.95a.75.75 0 01-1.06-1.06L4.94 6 3.05 4.11a.75.75 0 010-1.06z" />
                          </svg>
                        </button>
                      </Badge>
                    ))
                  )}
                </div>

                {/* Add new extension */}
                {editingItem.key === 'require_sidecar' ? (
                  // For require_sidecar: show checkboxes from photo_extensions
                  <div className="space-y-2">
                    <Label className="text-sm text-muted-foreground">
                      Select from photo extensions:
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {getPhotoExtensions().length === 0 ? (
                        <span className="text-sm text-muted-foreground italic">
                          No photo extensions defined. Add photo extensions first.
                        </span>
                      ) : (
                        getPhotoExtensions().map(ext => {
                          const isSelected = (editFormData.extensions || []).includes(ext)
                          return (
                            <Badge
                              key={ext}
                              variant={isSelected ? 'default' : 'outline'}
                              className="cursor-pointer"
                              onClick={() => {
                                setEditFormData(prev => {
                                  const current = prev.extensions || []
                                  if (isSelected) {
                                    return { ...prev, extensions: current.filter(e => e !== ext) }
                                  } else {
                                    return { ...prev, extensions: [...current, ext].sort() }
                                  }
                                })
                              }}
                            >
                              {ext}
                            </Badge>
                          )
                        })
                      )}
                    </div>
                  </div>
                ) : (
                  // For photo_extensions and metadata_extensions: free-form input
                  <div className="flex gap-2">
                    <Input
                      value={newExtensionInput}
                      onChange={e => setNewExtensionInput(e.target.value.toLowerCase())}
                      placeholder="e.g., .dng"
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          const ext = newExtensionInput.trim()
                          if (ext && !ext.startsWith('.')) {
                            setFormError('Extension must start with a dot (e.g., .dng)')
                            return
                          }
                          if (ext && !(editFormData.extensions || []).includes(ext)) {
                            setEditFormData(prev => ({
                              ...prev,
                              extensions: [...(prev.extensions || []), ext].sort()
                            }))
                            setNewExtensionInput('')
                            setFormError(null)
                          }
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        const ext = newExtensionInput.trim()
                        if (ext && !ext.startsWith('.')) {
                          setFormError('Extension must start with a dot (e.g., .dng)')
                          return
                        }
                        if (ext && !(editFormData.extensions || []).includes(ext)) {
                          setEditFormData(prev => ({
                            ...prev,
                            extensions: [...(prev.extensions || []), ext].sort()
                          }))
                          setNewExtensionInput('')
                          setFormError(null)
                        }
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            )}

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
            <Button onClick={handleEditSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={() => setDeleteDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Configuration</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingItem?.key}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
