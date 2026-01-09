import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, TestTube } from 'lucide-react'
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
  isConnectorRequiredForType
} from '@/types/schemas/collection'

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

function getConnectorsForType(connectors: Connector[], type: CollectionType): Connector[] {
  if (type === 'local') {
    return []
  }

  // Map collection type to connector type (they use the same values)
  return connectors.filter((connector) => connector.type === type && connector.is_active)
}

function getStateDescription(state: string): string {
  switch (state) {
    case 'live':
      return '1hr cache (default)'
    case 'closed':
      return '24hr cache (default)'
    case 'archived':
      return '7d cache (default)'
    default:
      return ''
  }
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

  const isEdit = !!collection

  // Initialize form with react-hook-form and Zod
  const form = useForm<CollectionFormData>({
    resolver: zodResolver(collectionFormSchema),
    defaultValues: {
      name: collection?.name || '',
      type: collection?.type || 'local',
      state: collection?.state || 'live',
      location: collection?.location || '',
      connector_id: collection?.connector_id || null,
      cache_ttl: collection?.cache_ttl || null,
      pipeline_id: collection?.pipeline_id || null
    }
  })

  // Get available active pipelines for selection
  const availablePipelines = pipelines.filter((p) => p.is_active)

  const selectedType = form.watch('type')
  const requiresConnector = isConnectorRequiredForType(selectedType)
  const availableConnectors = getConnectorsForType(connectors, selectedType)

  // Reset connector_id when switching to local type
  useEffect(() => {
    if (selectedType === 'local') {
      form.setValue('connector_id', null)
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
        connector_id: collection.connector_id,
        cache_ttl: collection.cache_ttl,
        pipeline_id: collection.pipeline_id
      })
    }
  }, [collection, form])

  const handleSubmit = async (data: CollectionFormData) => {
    setTestResult(null)
    await onSubmit(data)
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
              name="connector_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Connector</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(parseInt(value))}
                    value={field.value?.toString() || ''}
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
                          <SelectItem key={connector.id} value={connector.id.toString()}>
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
                  Determines default cache TTL and collection lifecycle
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Cache TTL (Optional) */}
          <FormField
            control={form.control}
            name="cache_ttl"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Cache TTL (Optional)</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    placeholder="3600"
                    value={field.value || ''}
                    onChange={(e) => {
                      const value = e.target.value
                      field.onChange(value ? parseInt(value) : null)
                    }}
                  />
                </FormControl>
                <FormDescription>
                  Custom cache TTL in seconds (overrides state-based default)
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Pipeline (Optional) */}
          <FormField
            control={form.control}
            name="pipeline_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Pipeline (Optional)</FormLabel>
                <Select
                  onValueChange={(value) => field.onChange(value === 'default' ? null : parseInt(value))}
                  value={field.value?.toString() || 'default'}
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
                        <SelectItem key={pipeline.id} value={pipeline.id.toString()}>
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
