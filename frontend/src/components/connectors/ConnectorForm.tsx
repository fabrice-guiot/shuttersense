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
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import type { Connector, ConnectorType } from '@/contracts/api/connector-api'
import {
  connectorFormSchema,
  getConnectorFormSchemaForType,
  type ConnectorFormData
} from '@/types/schemas/connector'

// ============================================================================
// Component Props
// ============================================================================

export interface ConnectorFormProps {
  connector?: Connector | null
  onSubmit: (data: ConnectorFormData) => Promise<void>
  onCancel: () => void
  onTestConnection?: (data: ConnectorFormData) => Promise<{ success: boolean; message: string }>
  loading?: boolean
  error?: string | null
  className?: string
}

// ============================================================================
// Helper Functions
// ============================================================================

// Connector types still in beta/QA - remove from this set once QA'd
const BETA_CONNECTOR_TYPES: Set<ConnectorType> = new Set(['s3', 'gcs', 'smb'])

function isBetaConnectorType(type: ConnectorType): boolean {
  return BETA_CONNECTOR_TYPES.has(type)
}

function getDefaultCredentials(type: ConnectorType) {
  switch (type) {
    case 's3':
      return {
        aws_access_key_id: '',
        aws_secret_access_key: '',
        region: '',
        bucket: ''
      }
    case 'gcs':
      return {
        service_account_json: '',
        bucket: ''
      }
    case 'smb':
      return {
        server: '',
        share: '',
        username: '',
        password: '',
        domain: ''
      }
  }
}

// ============================================================================
// Component
// ============================================================================

export default function ConnectorForm({
  connector,
  onSubmit,
  onCancel,
  onTestConnection,
  loading = false,
  error,
  className
}: ConnectorFormProps) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const isEdit = !!connector

  // Initialize form with react-hook-form and Zod
  const form = useForm<ConnectorFormData>({
    resolver: zodResolver(connectorFormSchema),
    defaultValues: {
      name: connector?.name || '',
      type: connector?.type || 's3',
      is_active: connector?.is_active ?? true,
      credentials: getDefaultCredentials(connector?.type || 's3')
    }
  })

  const selectedType = form.watch('type')

  // Reset credentials when type changes
  useEffect(() => {
    if (!isEdit) {
      form.setValue('credentials', getDefaultCredentials(selectedType))
    }
  }, [selectedType, isEdit, form])

  // Update form when connector prop changes
  useEffect(() => {
    if (connector) {
      form.reset({
        name: connector.name,
        type: connector.type,
        is_active: connector.is_active,
        credentials: getDefaultCredentials(connector.type)
      })
    }
  }, [connector, form])

  const handleSubmit = async (data: ConnectorFormData) => {
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
          {/* Connector Name */}
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Connector Name</FormLabel>
                <FormControl>
                  <Input placeholder="My S3 Connector" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Connector Type */}
          <FormField
            control={form.control}
            name="type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Connector Type</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                  disabled={isEdit}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select connector type" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="s3">
                      <span className="flex items-center gap-2">
                        Amazon S3
                        {isBetaConnectorType('s3') && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            Beta
                          </span>
                        )}
                      </span>
                    </SelectItem>
                    <SelectItem value="gcs">
                      <span className="flex items-center gap-2">
                        Google Cloud Storage
                        {isBetaConnectorType('gcs') && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            Beta
                          </span>
                        )}
                      </span>
                    </SelectItem>
                    <SelectItem value="smb">
                      <span className="flex items-center gap-2">
                        SMB/CIFS
                        {isBetaConnectorType('smb') && (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            Beta
                          </span>
                        )}
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
                {isEdit && (
                  <FormDescription>
                    Connector type cannot be changed after creation
                  </FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Active Status */}
          <FormField
            control={form.control}
            name="is_active"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel>Active</FormLabel>
                  <FormDescription>
                    Enable this connector for use in collections
                  </FormDescription>
                </div>
              </FormItem>
            )}
          />

          {/* Credentials Section */}
          <div className="space-y-4 rounded-lg border border-border bg-muted/50 p-4">
            <h3 className="text-sm font-semibold">Credentials</h3>

            {/* S3 Credentials */}
            {selectedType === 's3' && (
              <>
                <FormField
                  control={form.control}
                  name="credentials.aws_access_key_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>AWS Access Key ID</FormLabel>
                      <FormControl>
                        <Input placeholder="AKIAIOSFODNN7EXAMPLE" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.aws_secret_access_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>AWS Secret Access Key</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.region"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>AWS Region</FormLabel>
                      <FormControl>
                        <Input placeholder="us-east-1" {...field} />
                      </FormControl>
                      <FormDescription>
                        Format: region-location-number (e.g., us-east-1)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.bucket"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Default Bucket (Optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="my-photo-bucket" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            {/* GCS Credentials */}
            {selectedType === 'gcs' && (
              <>
                <FormField
                  control={form.control}
                  name="credentials.service_account_json"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Service Account JSON</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder='{"type": "service_account", "project_id": "...", ...}'
                          rows={8}
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Paste the entire JSON key file from Google Cloud Console
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.bucket"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Default Bucket (Optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="my-gcs-bucket" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            {/* SMB Credentials */}
            {selectedType === 'smb' && (
              <>
                <FormField
                  control={form.control}
                  name="credentials.server"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Server</FormLabel>
                      <FormControl>
                        <Input placeholder="192.168.1.100 or server.domain.com" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.share"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Share Name</FormLabel>
                      <FormControl>
                        <Input placeholder="Photos" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <Input placeholder="username" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password</FormLabel>
                      <FormControl>
                        <Input type="password" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="credentials.domain"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Domain (Optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="WORKGROUP" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}
          </div>

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
