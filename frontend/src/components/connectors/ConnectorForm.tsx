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
const BETA_CONNECTOR_TYPES: Set<ConnectorType> = new Set(['gcs', 'smb'])

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
  const [updateCredentials, setUpdateCredentials] = useState(false)

  const isEdit = !!connector

  // Initialize form with react-hook-form and Zod
  const form = useForm<ConnectorFormData>({
    resolver: zodResolver(connectorFormSchema),
    defaultValues: {
      name: connector?.name || '',
      type: connector?.type || 's3',
      credential_location: connector?.credential_location || 'server',
      is_active: connector?.is_active ?? true,
      credentials: getDefaultCredentials(connector?.type || 's3'),
      // For edit mode: false = keep existing credentials (skip validation)
      update_credentials: connector ? false : undefined
    }
  })

  const selectedType = form.watch('type')
  const credentialLocation = form.watch('credential_location')

  // Reset credentials when type changes
  useEffect(() => {
    if (!isEdit) {
      form.setValue('credentials', getDefaultCredentials(selectedType))
    }
  }, [selectedType, isEdit, form])

  // Auto-disable active status when credentials are pending
  useEffect(() => {
    if (credentialLocation === 'pending') {
      form.setValue('is_active', false)
    }
  }, [credentialLocation, form])

  // Update form when connector prop changes
  useEffect(() => {
    if (connector) {
      form.reset({
        name: connector.name,
        type: connector.type,
        credential_location: connector.credential_location || 'server',
        is_active: connector.is_active,
        credentials: connector.credential_location === 'server'
          ? getDefaultCredentials(connector.type)
          : undefined,
        // Edit mode: default to keeping existing credentials
        update_credentials: false
      })
      // Also reset the local state
      setUpdateCredentials(false)
    }
  }, [connector, form])

  const handleSubmit = async (data: ConnectorFormData) => {
    setTestResult(null)

    // Determine if we should include credentials:
    // - For new connectors with server credentials: always include
    // - For editing with server credentials: only if updateCredentials is true
    // - For agent/pending: never include
    const shouldIncludeCredentials =
      data.credential_location === 'server' &&
      (!isEdit || updateCredentials)

    const submitData: ConnectorFormData = {
      ...data,
      credentials: shouldIncludeCredentials ? data.credentials : undefined,
      // Tell the backend whether to update credentials (for edit mode)
      update_credentials: isEdit ? updateCredentials : undefined
    }

    await onSubmit(submitData)
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
                    disabled={credentialLocation === 'pending'}
                  />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel>Active</FormLabel>
                  <FormDescription>
                    {credentialLocation === 'pending'
                      ? 'Cannot activate until credentials are configured'
                      : 'Enable this connector for use in collections'}
                  </FormDescription>
                </div>
              </FormItem>
            )}
          />

          {/* Credential Storage Location */}
          <FormField
            control={form.control}
            name="credential_location"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Credential Storage</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                  disabled={isEdit}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select where to store credentials" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="server">
                      <span className="flex items-center gap-2">
                        Server (Encrypted)
                      </span>
                    </SelectItem>
                    {/* Agent option only shown when editing a connector that already has agent credentials */}
                    {isEdit && credentialLocation === 'agent' && (
                      <SelectItem value="agent">
                        <span className="flex items-center gap-2">
                          Agent Only
                        </span>
                      </SelectItem>
                    )}
                    <SelectItem value="pending">
                      <span className="flex items-center gap-2">
                        Pending Agent Configuration
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  {credentialLocation === 'server' && 'Credentials encrypted and stored on the server'}
                  {credentialLocation === 'agent' && 'Credentials configured on agent via CLI'}
                  {credentialLocation === 'pending' && 'Credentials will be configured on an agent via CLI'}
                </FormDescription>
                {isEdit && (
                  <FormDescription className="text-amber-600 dark:text-amber-400">
                    Credential storage location cannot be changed after creation
                  </FormDescription>
                )}
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Credentials Section - only shown for server storage */}
          {credentialLocation === 'server' && (
          <div className="space-y-4 rounded-lg border border-border bg-muted/50 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Credentials</h3>
              {isEdit && (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="update-credentials"
                    checked={updateCredentials}
                    onCheckedChange={(checked) => {
                      setUpdateCredentials(checked === true)
                      // Update form value for validation
                      form.setValue('update_credentials', checked === true)
                    }}
                  />
                  <label
                    htmlFor="update-credentials"
                    className="text-sm font-medium cursor-pointer"
                  >
                    Update credentials
                  </label>
                </div>
              )}
            </div>

            {/* Show existing credentials message or credential fields */}
            {isEdit && !updateCredentials ? (
              <p className="text-sm text-muted-foreground">
                Credentials are securely stored. Enable "Update credentials" to change them.
              </p>
            ) : (
              <>

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
              </>
            )}
          </div>
          )}

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
              {onTestConnection && credentialLocation === 'server' && (
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
