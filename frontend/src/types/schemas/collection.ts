/**
 * Collection Form Validation Schemas
 *
 * Zod schemas for collection forms with type-safe validation
 */

import { z } from 'zod'
import type { CollectionType } from '@/contracts/api/collection-api'

// ============================================================================
// Collection Form Schema
// ============================================================================

/**
 * Base collection form schema
 */
export const collectionFormSchema = z
  .object({
    name: z
      .string()
      .min(1, 'Collection name is required')
      .max(100, 'Collection name must be less than 100 characters')
      .regex(
        /^[a-zA-Z0-9\s\-_]+$/,
        'Collection name can only contain letters, numbers, spaces, hyphens, and underscores'
      ),
    type: z.enum(['local', 's3', 'gcs', 'smb'], {
      message: 'Invalid collection type'
    }),
    state: z.enum(['live', 'closed', 'archived'], {
      message: 'Invalid collection state'
    }),
    location: z
      .string()
      .min(1, 'Location is required')
      .max(500, 'Location must be less than 500 characters'),
    connector_guid: z
      .string()
      .min(1, 'Connector is required')
      .nullable(),
    cache_ttl: z
      .number()
      .int('Cache TTL must be an integer')
      .positive('Cache TTL must be positive')
      .nullable()
      .optional(),
    pipeline_guid: z
      .string()
      .nullable()
      .optional()
  })
  .refine(
    (data) => {
      // local type must have null connector_guid
      if (data.type === 'local') {
        return data.connector_guid === null
      }
      return true
    },
    {
      message: 'Local collections cannot have a connector',
      path: ['connector_guid']
    }
  )
  .refine(
    (data) => {
      // Remote types (s3, gcs, smb) must have non-null connector_guid
      if (data.type !== 'local') {
        return data.connector_guid !== null && data.connector_guid.length > 0
      }
      return true
    },
    {
      message: 'Remote collections require a connector',
      path: ['connector_guid']
    }
  )

// ============================================================================
// Type Inference
// ============================================================================

export type CollectionFormData = z.infer<typeof collectionFormSchema>

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if a collection type requires a connector
 */
export function isConnectorRequiredForType(type: CollectionType): boolean {
  return type !== 'local'
}

/**
 * Get default form values for a collection type
 */
export function getDefaultCollectionFormValues(type: CollectionType = 'local'): Partial<CollectionFormData> {
  return {
    name: '',
    type,
    state: 'live',
    location: '',
    connector_guid: type === 'local' ? null : undefined,
    cache_ttl: null,
    pipeline_guid: null
  }
}
