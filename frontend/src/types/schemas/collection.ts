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
        /^[a-zA-Z0-9\s\-_.'()&,]+$/,
        'Collection name can only contain letters, numbers, spaces, and common punctuation (- _ . \' ( ) & ,)'
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
      .union([
        z.string().min(1, 'Connector is required'),
        z.null()
      ])
      .optional()
      .transform((val) => val ?? null),  // Convert undefined to null
    pipeline_guid: z
      .string()
      .nullable()
      .optional(),
    bound_agent_guid: z
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
  .refine(
    (data) => {
      // bound_agent_guid is only valid for LOCAL collections
      if (data.type !== 'local' && data.bound_agent_guid) {
        return false
      }
      return true
    },
    {
      message: 'Bound agent is only valid for LOCAL collections',
      path: ['bound_agent_guid']
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
    pipeline_guid: null,
    bound_agent_guid: null
  }
}

/**
 * Check if a collection type supports bound agents
 */
export function supportsAgentBinding(type: CollectionType): boolean {
  return type === 'local'
}
