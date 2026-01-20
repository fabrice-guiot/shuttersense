/**
 * Connector Form Validation Schemas
 *
 * Zod schemas for connector forms with type-safe validation
 */

import { z } from 'zod'
import type { ConnectorType } from '@/contracts/api/connector-api'

// ============================================================================
// Credential Location Schema
// ============================================================================

/**
 * Credential location for connectors
 * - server: Credentials stored encrypted on server
 * - agent: Credentials stored on agent only
 * - pending: No credentials configured yet
 */
export const credentialLocationSchema = z.enum(['server', 'agent', 'pending'])

// ============================================================================
// Credential Schemas
// ============================================================================

/**
 * S3 Credentials Schema
 */
export const s3CredentialsSchema = z.object({
  aws_access_key_id: z
    .string()
    .min(1, 'Access Key ID is required')
    .max(128, 'Access Key ID is too long'),
  aws_secret_access_key: z
    .string()
    .min(1, 'Secret Access Key is required')
    .max(128, 'Secret Access Key is too long'),
  region: z
    .string()
    .min(1, 'Region is required')
    .regex(/^[a-z]{2}-[a-z]+-\d{1}$/, 'Invalid AWS region format (e.g., us-east-1)'),
  bucket: z
    .string()
    .optional()
    .refine(
      (val) => !val || /^[a-z0-9][a-z0-9.-]*[a-z0-9]$/.test(val),
      'Invalid S3 bucket name format'
    )
})

/**
 * GCS Credentials Schema
 */
export const gcsCredentialsSchema = z.object({
  service_account_json: z
    .string()
    .min(1, 'Service Account JSON is required')
    .refine(
      (val) => {
        try {
          const parsed = JSON.parse(val)
          return parsed.type === 'service_account' && parsed.project_id && parsed.private_key
        } catch {
          return false
        }
      },
      'Invalid GCS service account JSON format'
    ),
  bucket: z
    .string()
    .optional()
    .refine(
      (val) => !val || /^[a-z0-9][a-z0-9._-]*[a-z0-9]$/.test(val),
      'Invalid GCS bucket name format'
    )
})

/**
 * SMB Credentials Schema
 */
export const smbCredentialsSchema = z.object({
  server: z
    .string()
    .min(1, 'Server address is required')
    .max(255, 'Server address is too long'),
  share: z
    .string()
    .min(1, 'Share name is required')
    .max(255, 'Share name is too long'),
  username: z
    .string()
    .min(1, 'Username is required')
    .max(255, 'Username is too long'),
  password: z
    .string()
    .min(1, 'Password is required')
    .max(255, 'Password is too long'),
  domain: z
    .string()
    .max(255, 'Domain is too long')
    .optional()
})

/**
 * Union type for all credential schemas
 */
export const credentialsSchema = z.union([
  s3CredentialsSchema,
  gcsCredentialsSchema,
  smbCredentialsSchema
])

// ============================================================================
// Connector Form Schema
// ============================================================================

/**
 * Base connector form schema (without credentials)
 */
export const connectorBaseSchema = z.object({
  name: z
    .string()
    .min(1, 'Connector name is required')
    .max(100, 'Connector name must be less than 100 characters')
    .regex(/^[a-zA-Z0-9\s\-_]+$/, 'Connector name can only contain letters, numbers, spaces, hyphens, and underscores'),
  type: z.enum(['s3', 'gcs', 'smb'], {
    message: 'Invalid connector type'
  }),
  credential_location: credentialLocationSchema,
  is_active: z.boolean()
})

/**
 * Full connector form schema with dynamic credentials
 *
 * Credentials are required when credential_location is 'server' AND update_credentials is true.
 * For editing existing connectors, update_credentials can be false to skip credential validation.
 * Credentials should not be provided when 'agent' or 'pending'.
 * Validates credentials based on the selected connector type.
 */
export const connectorFormSchema = connectorBaseSchema
  .extend({
    credentials: z.any().optional(),
    // For edit mode: false = keep existing credentials, true = update with new credentials
    update_credentials: z.boolean().optional()
  })
  .superRefine((data, ctx) => {
    // Skip credentials validation if not storing on server
    if (data.credential_location !== 'server') {
      return
    }

    // Skip credentials validation if update_credentials is explicitly false (edit mode)
    if (data.update_credentials === false) {
      return
    }

    // Credentials required when credential_location is 'server' and updating
    if (!data.credentials) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Credentials are required when storing on server',
        path: ['credentials']
      })
      return
    }

    // Validate credentials based on connector type
    let credSchema: z.ZodTypeAny
    switch (data.type) {
      case 's3':
        credSchema = s3CredentialsSchema
        break
      case 'gcs':
        credSchema = gcsCredentialsSchema
        break
      case 'smb':
        credSchema = smbCredentialsSchema
        break
      default:
        return
    }

    const result = credSchema.safeParse(data.credentials)
    if (!result.success) {
      // Add each credential validation error with the proper path
      result.error.issues.forEach((issue) => {
        ctx.addIssue({
          ...issue,
          path: ['credentials', ...issue.path]
        })
      })
    }
  })

/**
 * S3 Connector Form Schema (specific type)
 */
export const s3ConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('s3'),
  credentials: s3CredentialsSchema
})

/**
 * GCS Connector Form Schema (specific type)
 */
export const gcsConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('gcs'),
  credentials: gcsCredentialsSchema
})

/**
 * SMB Connector Form Schema (specific type)
 */
export const smbConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('smb'),
  credentials: smbCredentialsSchema
})

// ============================================================================
// Type Inference
// ============================================================================

export type ConnectorFormData = z.infer<typeof connectorFormSchema>
export type S3CredentialsFormData = z.infer<typeof s3CredentialsSchema>
export type GCSCredentialsFormData = z.infer<typeof gcsCredentialsSchema>
export type SMBCredentialsFormData = z.infer<typeof smbCredentialsSchema>

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the appropriate credentials schema for a connector type
 */
export function getCredentialsSchemaForType(type: ConnectorType) {
  switch (type) {
    case 's3':
      return s3CredentialsSchema
    case 'gcs':
      return gcsCredentialsSchema
    case 'smb':
      return smbCredentialsSchema
    default:
      throw new Error(`Unknown connector type: ${type}`)
  }
}

/**
 * Get the appropriate connector form schema for a connector type
 */
export function getConnectorFormSchemaForType(type: ConnectorType) {
  switch (type) {
    case 's3':
      return s3ConnectorFormSchema
    case 'gcs':
      return gcsConnectorFormSchema
    case 'smb':
      return smbConnectorFormSchema
    default:
      throw new Error(`Unknown connector type: ${type}`)
  }
}
