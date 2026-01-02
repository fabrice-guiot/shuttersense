/**
 * Connector Form Validation Schemas
 *
 * Zod schemas for connector forms with type-safe validation
 */

import { z } from 'zod'
import type { ConnectorType } from '@/contracts/api/connector-api'

// ============================================================================
// Credential Schemas
// ============================================================================

/**
 * S3 Credentials Schema
 */
export const s3CredentialsSchema = z.object({
  access_key_id: z
    .string()
    .min(1, 'Access Key ID is required')
    .max(128, 'Access Key ID is too long'),
  secret_access_key: z
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
  type: z.enum(['S3', 'GCS', 'SMB'], {
    required_error: 'Connector type is required',
    invalid_type_error: 'Invalid connector type'
  }),
  active: z.boolean().default(true)
})

/**
 * Full connector form schema with dynamic credentials
 */
export const connectorFormSchema = connectorBaseSchema.extend({
  credentials: credentialsSchema
})

/**
 * S3 Connector Form Schema (specific type)
 */
export const s3ConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('S3'),
  credentials: s3CredentialsSchema
})

/**
 * GCS Connector Form Schema (specific type)
 */
export const gcsConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('GCS'),
  credentials: gcsCredentialsSchema
})

/**
 * SMB Connector Form Schema (specific type)
 */
export const smbConnectorFormSchema = connectorBaseSchema.extend({
  type: z.literal('SMB'),
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
    case 'S3':
      return s3CredentialsSchema
    case 'GCS':
      return gcsCredentialsSchema
    case 'SMB':
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
    case 'S3':
      return s3ConnectorFormSchema
    case 'GCS':
      return gcsConnectorFormSchema
    case 'SMB':
      return smbConnectorFormSchema
    default:
      throw new Error(`Unknown connector type: ${type}`)
  }
}
