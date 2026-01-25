/**
 * InventoryConfigForm Component
 *
 * Form for configuring S3/GCS inventory settings on a connector.
 * Supports both provider types with provider-specific fields.
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
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
import type {
  InventoryConfig,
  InventorySchedule,
  InventoryProvider
} from '@/contracts/api/inventory-api'
import type { ConnectorType } from '@/contracts/api/connector-api'

// ============================================================================
// Form Schema
// ============================================================================

const s3InventorySchema = z.object({
  provider: z.literal('s3'),
  destination_bucket: z.string().min(3, 'Bucket name required').max(63),
  source_bucket: z.string().min(3, 'Bucket name required').max(63),
  config_name: z.string().min(1, 'Config name required').max(64),
  format: z.enum(['CSV', 'ORC', 'Parquet'] as const)
})

const gcsInventorySchema = z.object({
  provider: z.literal('gcs'),
  destination_bucket: z.string().min(3, 'Bucket name required').max(63),
  report_config_name: z.string().min(1, 'Report config name required').max(128),
  format: z.enum(['CSV', 'Parquet'] as const)
})

const inventoryFormSchema = z.object({
  config: z.discriminatedUnion('provider', [s3InventorySchema, gcsInventorySchema]),
  schedule: z.enum(['manual', 'daily', 'weekly'] as const)
})

type InventoryFormData = z.infer<typeof inventoryFormSchema>

// ============================================================================
// Component Props
// ============================================================================

export interface InventoryConfigFormProps {
  /** Connector type (s3 or gcs) - determines form fields */
  connectorType: ConnectorType
  /** Existing config to edit (null for new config) */
  existingConfig?: InventoryConfig | null
  /** Existing schedule */
  existingSchedule?: InventorySchedule
  /** Form submission handler */
  onSubmit: (config: InventoryConfig, schedule: InventorySchedule) => Promise<void>
  /** Cancel handler */
  onCancel: () => void
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string | null
  /** Additional CSS class */
  className?: string
}

// ============================================================================
// Component
// ============================================================================

export function InventoryConfigForm({
  connectorType,
  existingConfig,
  existingSchedule = 'manual',
  onSubmit,
  onCancel,
  loading = false,
  error,
  className
}: InventoryConfigFormProps) {
  // Determine provider from connector type
  const provider: InventoryProvider = connectorType === 'gcs' ? 'gcs' : 's3'

  // Build default values based on provider
  const getDefaultValues = (): InventoryFormData => {
    if (existingConfig) {
      return {
        config: existingConfig,
        schedule: existingSchedule
      }
    }

    if (provider === 's3') {
      return {
        config: {
          provider: 's3',
          destination_bucket: '',
          source_bucket: '',
          config_name: '',
          format: 'CSV' as const
        },
        schedule: 'manual'
      }
    }

    return {
      config: {
        provider: 'gcs',
        destination_bucket: '',
        report_config_name: '',
        format: 'CSV' as const
      },
      schedule: 'manual'
    }
  }

  const form = useForm<InventoryFormData>({
    resolver: zodResolver(inventoryFormSchema),
    defaultValues: getDefaultValues()
  })

  // Reset form when existingConfig changes
  useEffect(() => {
    form.reset(getDefaultValues())
  }, [existingConfig, existingSchedule]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async (data: InventoryFormData) => {
    await onSubmit(data.config, data.schedule)
  }

  const isS3 = provider === 's3'

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className={className}>
        <div className="space-y-4">
          {/* Provider Info */}
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-sm text-muted-foreground">
              {isS3 ? (
                <>
                  Configure <strong>S3 Inventory</strong> to import file metadata from your S3 bucket
                  without making per-object API calls.
                </>
              ) : (
                <>
                  Configure <strong>GCS Storage Insights</strong> to import file metadata from your
                  Cloud Storage bucket.
                </>
              )}
            </p>
          </div>

          {/* S3-specific fields */}
          {isS3 && (
            <>
              <FormField
                control={form.control}
                name="config.source_bucket"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Source Bucket</FormLabel>
                    <FormControl>
                      <Input placeholder="my-photo-bucket" {...field} />
                    </FormControl>
                    <FormDescription>
                      The bucket being inventoried (your photo storage bucket)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="config.destination_bucket"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination Bucket</FormLabel>
                    <FormControl>
                      <Input placeholder="my-inventory-bucket" {...field} />
                    </FormControl>
                    <FormDescription>
                      The bucket where S3 stores inventory reports
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="config.config_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Inventory Configuration Name</FormLabel>
                    <FormControl>
                      <Input placeholder="daily-inventory" {...field} />
                    </FormControl>
                    <FormDescription>
                      The name of your S3 Inventory configuration (from AWS Console)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="config.format"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Inventory Format</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select format" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="CSV">CSV</SelectItem>
                        <SelectItem value="ORC">ORC</SelectItem>
                        <SelectItem value="Parquet">Parquet</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Format configured in your S3 Inventory settings
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </>
          )}

          {/* GCS-specific fields */}
          {!isS3 && (
            <>
              <FormField
                control={form.control}
                name="config.destination_bucket"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination Bucket</FormLabel>
                    <FormControl>
                      <Input placeholder="my-inventory-bucket" {...field} />
                    </FormControl>
                    <FormDescription>
                      The bucket where Storage Insights stores reports
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="config.report_config_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Report Configuration Name</FormLabel>
                    <FormControl>
                      <Input placeholder="photo-inventory" {...field} />
                    </FormControl>
                    <FormDescription>
                      The name of your Storage Insights report configuration
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="config.format"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Report Format</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select format" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="CSV">CSV</SelectItem>
                        <SelectItem value="Parquet">Parquet</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      Format configured in your Storage Insights settings
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </>
          )}

          {/* Schedule Selection */}
          <FormField
            control={form.control}
            name="schedule"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Import Schedule</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select schedule" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="manual">Manual only</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
                <FormDescription>
                  {field.value === 'manual' && 'Import only when manually triggered'}
                  {field.value === 'daily' && 'Automatically import once per day at 00:00 UTC'}
                  {field.value === 'weekly' && 'Automatically import once per week at 00:00 UTC'}
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : existingConfig ? (
                'Update Configuration'
              ) : (
                'Save Configuration'
              )}
            </Button>
          </div>
        </div>
      </form>
    </Form>
  )
}

export default InventoryConfigForm
