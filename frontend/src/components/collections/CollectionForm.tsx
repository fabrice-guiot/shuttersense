import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, TestTube, Bot, CalendarClock } from 'lucide-react'
import { formatDateTime } from '@/utils/dateFormat'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { Collection, CollectionType } from '@/contracts/api/collection-api'
import type { Connector } from '@/contracts/api/connector-api'
import type { PipelineSummary } from '@/contracts/api/pipelines-api'
import {
  collectionFormSchema,
  type CollectionFormData,
  isConnectorRequiredForType,
  supportsAgentBinding
} from '@/types/schemas/collection'
import { useOnlineAgents, type OnlineAgent } from '@/hooks/useOnlineAgents'

// ============================================================================
// Beta Collection Types
// ============================================================================

// Collection types still in beta/QA - remove from this set once QA'd
const BETA_COLLECTION_TYPES: Set<CollectionType> = new Set(['gcs', 'smb'])

function isBetaCollectionType(type: CollectionType): boolean {
  return BETA_COLLECTION_TYPES.has(type)
}

// Beta chip component for consistent styling
function BetaChip() {
  return (
    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
      Beta
    </span>
  )
}

// ============================================================================
// Component Props
// ============================================================================

export interface CollectionFormProps {
  collection?: Collection | null
  connectors: Connector[]
  pipelines?: PipelineSummary[]
  onSubmit: (data: CollectionFormData) => Promise<void>
  onCancel: () => void
  onTestConnection?: (data: CollectionFormData) => Promise<{ success: boolean; message: string }>
  loading?: boolean
  error?: string | null
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

function getConnectorsForType(
  connectors: Connector[],
  type: CollectionType,
  currentConnectorGuid?: string | null
): Connector[] {
  if (type === 'local') {
    return []
  }

  // Map collection type to connector type (they use the same values)
  // Include active connectors of matching type, plus the current connector if assigned
  // (even if inactive, to allow editing without losing the assignment)
  return connectors.filter(
    (connector) =>
      (connector.type === type && connector.is_active) ||
      (currentConnectorGuid && connector.guid === currentConnectorGuid)
  )
}

function getStateDescription(state: string): string {
  switch (state) {
    case 'live':
      return 'Active work, frequent changes'
    case 'closed':
      return 'Finished work, infrequent changes'
    case 'archived':
      return 'Long-term storage'
    default:
      return ''
  }
}

/**
 * Calculate the next expected refresh datetime based on last scan and TTL
 */
function calculateNextRefresh(
  lastScannedAt: string | null,
  cacheTtl: number | null
): { datetime: string | null; label: string } {
  if (!lastScannedAt) {
    return { datetime: null, label: 'Never scanned' }
  }

  if (!cacheTtl || cacheTtl <= 0) {
    return { datetime: null, label: 'Auto-refresh disabled' }
  }

  const lastScan = new Date(lastScannedAt)
  const nextRefresh = new Date(lastScan.getTime() + cacheTtl * 1000)
  const now = new Date()

  if (nextRefresh <= now) {
    return { datetime: nextRefresh.toISOString(), label: 'Refresh pending' }
  }

  return { datetime: nextRefresh.toISOString(), label: formatDateTime(nextRefresh.toISOString()) }
}

// ============================================================================
// Component
// ============================================================================

export default function CollectionForm({
  collection,
  connectors,
  pipelines = [],
  onSubmit,
  onCancel,
  onTestConnection,
  loading = false,
  error,
  className
}: CollectionFormProps) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  // Fetch online agents for LOCAL collection binding
  const { onlineAgents, loading: agentsLoading } = useOnlineAgents()

  const isEdit = !!collection

  // Initialize form with react-hook-form and Zod
  const form = useForm<CollectionFormData>({
    resolver: zodResolver(collectionFormSchema),
    defaultValues: {
      name: collection?.name || '',
      type: collection?.type || 'local',
      state: collection?.state || 'live',
      location: collection?.location || '',
      connector_guid: collection?.connector_guid || null,
      pipeline_guid: collection?.pipeline_guid || null,
      bound_agent_guid: collection?.bound_agent?.guid || null
    }
  })

  // Get available active pipelines for selection
  const availablePipelines = pipelines.filter((p) => p.is_active)

  const selectedType = form.watch('type')
  const requiresConnector = isConnectorRequiredForType(selectedType)
  const showAgentSelector = supportsAgentBinding(selectedType)
  const availableConnectors = getConnectorsForType(connectors, selectedType, collection?.connector_guid)

  // Reset connector_guid when switching to local type, reset bound_agent_guid when switching to remote
  useEffect(() => {
    if (selectedType === 'local') {
      form.setValue('connector_guid', null)
    } else {
      form.setValue('bound_agent_guid', null)
    }
  }, [selectedType, form])

  // Update form when collection prop changes
  useEffect(() => {
    if (collection) {
      form.reset({
        name: collection.name,
        type: collection.type,
        state: collection.state,
        location: collection.location,
        connector_guid: collection.connector_guid,
        pipeline_guid: collection.pipeline_guid,
        bound_agent_guid: collection.bound_agent?.guid || null
      })
    }
  }, [collection, form])

  const handleSubmit = async (data: CollectionFormData) => {
    console.log('[CollectionForm] handleSubmit called with data:', data)
    setTestResult(null)
    await onSubmit(data)
  }

  // Debug: Log form errors when they change
  const formErrors = form.formState.errors
  if (Object.keys(formErrors).length > 0) {
    console.log('[CollectionForm] Form validation errors:', formErrors)
  }

  const handleTestConnection = async () => {
    if (!onTestConnection) return

    setTesting(true)
    setTestResult(null)

    try {
      const data = form.getValues()
      const result = await onTestConnection(data)
      setTestResult(result)
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Connection test failed'
      })
    } finally {
      setTesting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className={className}>
        <div className="space-y-4">
          {/* Collection Name */}
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Collection Name</FormLabel>
                <FormControl>
                  <Input placeholder="My Photo Collection" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Collection Type */}
          <FormField
            control={form.control}
            name="type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Collection Type</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                  disabled={isEdit}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select collection type" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="local">Local Filesystem</SelectItem>
                    <SelectItem value="s3">Amazon S3</SelectItem>
                    <SelectItem value="gcs">
                      <span className="flex items-center gap-2">
                        Google Cloud Storage
                        {isBetaCollectionType('gcs') && <BetaChip />}
                      </span>
                    </SelectItem>
                    <SelectItem value="smb">
                      <span className="flex items-center gap-2">
                        SMB/CIFS
                        {isBetaCollectionType('smb') && <BetaChip />}
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
                {isEdit && (
                  <FormDescription>
                    Collection type cannot be changed after creation
                  </FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Connector (only for remote types) */}
          {requiresConnector && (
            <FormField
              control={form.control}
              name="connector_guid"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Connector</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value)}
                    value={field.value || ''}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a connector" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {availableConnectors.length === 0 ? (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          No active {selectedType} connectors available
                        </div>
                      ) : (
                        availableConnectors.map((connector) => (
                          <SelectItem key={connector.guid} value={connector.guid}>
                            {connector.name}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Select an active {selectedType} connector for this collection
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}

          {/* Location */}
          <FormField
            control={form.control}
            name="location"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Location</FormLabel>
                <FormControl>
                  <Input
                    placeholder={
                      selectedType === 'local'
                        ? '/absolute/path/to/photos'
                        : 'bucket-name/prefix or s3://bucket/path'
                    }
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  {selectedType === 'local'
                    ? 'Absolute filesystem path to photo directory'
                    : 'Bucket name and optional prefix/path'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Bound Agent (only for LOCAL collections) */}
          {showAgentSelector && (
            <FormField
              control={form.control}
              name="bound_agent_guid"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    Bound Agent (Optional)
                  </FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === 'none' ? null : value)}
                    value={field.value || 'none'}
                    disabled={agentsLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select an agent..." />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">No bound agent (any agent)</SelectItem>
                      {onlineAgents.length === 0 ? (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          No online agents available
                        </div>
                      ) : (
                        onlineAgents.map((agent) => (
                          <SelectItem key={agent.guid} value={agent.guid}>
                            <span className="flex items-center gap-2">
                              <span className="h-2 w-2 rounded-full bg-green-500" />
                              {agent.name}
                              <span className="text-xs text-muted-foreground">({agent.hostname})</span>
                            </span>
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Bind this collection to a specific agent for local filesystem access.
                    Only online agents are shown.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          )}

          {/* Collection State */}
          <FormField
            control={form.control}
            name="state"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Collection State</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select state" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="live">
                      Live - {getStateDescription('live')}
                    </SelectItem>
                    <SelectItem value="closed">
                      Closed - {getStateDescription('closed')}
                    </SelectItem>
                    <SelectItem value="archived">
                      Archived - {getStateDescription('archived')}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  Collection lifecycle stage. Cache TTL is configured per-state in Settings.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Next Expected Refresh (read-only, only for existing collections) */}
          {isEdit && collection && (
            <div className="rounded-md border border-border bg-muted/50 p-3">
              <div className="flex items-center gap-2 text-sm">
                <CalendarClock className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Next Scheduled Refresh:</span>
                <span className="text-muted-foreground">
                  {(() => {
                    const result = calculateNextRefresh(collection.last_scanned_at, collection.cache_ttl)
                    return result.label
                  })()}
                </span>
              </div>
              {collection.last_scanned_at && (
                <div className="mt-1 ml-6 text-xs text-muted-foreground">
                  Last scanned: {formatDateTime(collection.last_scanned_at)}
                </div>
              )}
            </div>
          )}

          {/* Pipeline (Optional) */}
          <FormField
            control={form.control}
            name="pipeline_guid"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Pipeline (Optional)</FormLabel>
                <Select
                  onValueChange={(value) => field.onChange(value === 'default' ? null : value)}
                  value={field.value || 'default'}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Use default pipeline" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="default">Use default pipeline</SelectItem>
                    {availablePipelines.length === 0 ? (
                      <div className="px-2 py-1.5 text-sm text-muted-foreground">
                        No active pipelines available
                      </div>
                    ) : (
                      availablePipelines.map((pipeline) => (
                        <SelectItem key={pipeline.guid} value={pipeline.guid}>
                          <span className="flex items-center gap-2">
                            {pipeline.name}
                            {pipeline.is_default && (
                              <span className="text-xs text-muted-foreground">(default)</span>
                            )}
                          </span>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                <FormDescription>
                  Pin this collection to a specific pipeline, or use the default at runtime
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Test Result */}
          {testResult && (
            <Alert variant={testResult.success ? 'default' : 'destructive'}>
              <AlertDescription>{testResult.message}</AlertDescription>
            </Alert>
          )}

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex justify-between gap-2 pt-4">
            <div>
              {onTestConnection && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={testing || loading}
                  className="gap-2"
                >
                  {testing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <TestTube className="h-4 w-4" />
                      Test Connection
                    </>
                  )}
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {isEdit ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  <>{isEdit ? 'Update' : 'Create'}</>
                )}
              </Button>
            </div>
          </div>
        </div>
      </form>
    </Form>
  )
}
