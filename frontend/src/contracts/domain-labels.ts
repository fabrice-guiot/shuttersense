/**
 * Domain Labels Registry
 *
 * Centralized source of truth for all domain model display labels, icons,
 * and visual mappings. Import from this file to ensure UI consistency.
 *
 * See frontend/docs/design-system.md for usage guidelines.
 */

import {
  FolderOpen,
  Plug,
  Workflow,
  Archive,
  BarChart3,
  Settings,
  Users,
  LayoutGrid,
  Cloud,
  HardDrive,
  type LucideIcon
} from 'lucide-react'

import type { ConnectorType } from './api/connector-api'
import type { CollectionType, CollectionState } from './api/collection-api'

// ============================================================================
// Domain Object Icons
// ============================================================================

/**
 * Icons for primary domain objects
 * Use these consistently in navigation, headers, and FK references
 */
export const DOMAIN_ICONS = {
  dashboard: LayoutGrid,
  collection: FolderOpen,
  connector: Plug,
  pipeline: Workflow,
  asset: Archive,
  analytics: BarChart3,
  team: Users,
  settings: Settings,
} as const satisfies Record<string, LucideIcon>

export type DomainType = keyof typeof DOMAIN_ICONS

// ============================================================================
// Connector Types
// ============================================================================

/**
 * Human-readable labels for connector types
 */
export const CONNECTOR_TYPE_LABELS: Record<ConnectorType, string> = {
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

/**
 * Icons for connector types
 */
export const CONNECTOR_TYPE_ICONS: Record<ConnectorType, LucideIcon> = {
  s3: Cloud,
  gcs: Cloud,
  smb: HardDrive
}

/**
 * Short labels for compact display
 */
export const CONNECTOR_TYPE_SHORT_LABELS: Record<ConnectorType, string> = {
  s3: 'S3',
  gcs: 'GCS',
  smb: 'SMB'
}

// ============================================================================
// Collection Types
// ============================================================================

/**
 * Human-readable labels for collection types
 */
export const COLLECTION_TYPE_LABELS: Record<CollectionType, string> = {
  local: 'Local',
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

/**
 * Short labels for compact display
 */
export const COLLECTION_TYPE_SHORT_LABELS: Record<CollectionType, string> = {
  local: 'Local',
  s3: 'S3',
  gcs: 'GCS',
  smb: 'SMB'
}

// ============================================================================
// Collection States
// ============================================================================

/**
 * Human-readable labels for collection states
 */
export const COLLECTION_STATE_LABELS: Record<CollectionState, string> = {
  live: 'Live',
  closed: 'Closed',
  archived: 'Archived'
}

/**
 * Badge variants for collection states
 * Maps to Badge component variants
 */
export const COLLECTION_STATE_BADGE_VARIANT: Record<
  CollectionState,
  'success' | 'muted' | 'info'
> = {
  live: 'success',
  closed: 'muted',
  archived: 'info'
}

/**
 * Descriptions for collection states
 */
export const COLLECTION_STATE_DESCRIPTIONS: Record<CollectionState, string> = {
  live: 'Active collection, frequently accessed',
  closed: 'Inactive collection, not accepting new items',
  archived: 'Historical collection, read-only access'
}

// ============================================================================
// Accessibility Status
// ============================================================================

export type AccessibilityStatus = 'accessible' | 'not_accessible'

export const ACCESSIBILITY_STATUS_CONFIG = {
  accessible: {
    label: 'Accessible',
    badgeVariant: 'success' as const,
    description: 'Collection can be read and scanned'
  },
  not_accessible: {
    label: 'Not Accessible',
    badgeVariant: 'destructive' as const,
    description: 'Connection or permission error'
  }
} as const

// ============================================================================
// Active/Inactive Status
// ============================================================================

export const ACTIVE_STATUS_CONFIG = {
  active: {
    label: 'Active',
    badgeVariant: 'default' as const,
    description: 'Currently enabled'
  },
  inactive: {
    label: 'Inactive',
    badgeVariant: 'outline' as const,
    description: 'Currently disabled'
  }
} as const

// ============================================================================
// Enabled/Disabled Feature Status (e.g., Pipelines)
// ============================================================================

export const ENABLED_STATUS_CONFIG = {
  enabled: {
    label: 'Enabled',
    badgeVariant: 'success' as const,
    dotColor: 'bg-green-500',
    description: 'Feature is active'
  },
  disabled: {
    label: 'Disabled',
    badgeVariant: 'muted' as const,
    dotColor: 'bg-gray-400',
    description: 'Feature is inactive'
  }
} as const

// ============================================================================
// Filter Options
// ============================================================================

/**
 * Options for collection state filter dropdowns
 */
export const COLLECTION_STATE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All States' },
  { value: 'live', label: 'Live' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived' }
] as const

/**
 * Options for collection type filter dropdowns
 */
export const COLLECTION_TYPE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All Types' },
  { value: 'local', label: 'Local' },
  { value: 's3', label: 'Amazon S3' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'smb', label: 'SMB/CIFS' }
] as const

/**
 * Options for connector type filter dropdowns
 */
export const CONNECTOR_TYPE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All Types' },
  { value: 's3', label: 'Amazon S3' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'smb', label: 'SMB/CIFS' }
] as const

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get the icon component for a domain type
 */
export function getDomainIcon(domain: DomainType): LucideIcon {
  return DOMAIN_ICONS[domain]
}

/**
 * Get the label for a connector type
 */
export function getConnectorTypeLabel(type: ConnectorType): string {
  return CONNECTOR_TYPE_LABELS[type] || type
}

/**
 * Get the label for a collection type
 */
export function getCollectionTypeLabel(type: CollectionType): string {
  return COLLECTION_TYPE_LABELS[type] || type
}

/**
 * Get the label for a collection state
 */
export function getCollectionStateLabel(state: CollectionState): string {
  return COLLECTION_STATE_LABELS[state] || state
}

/**
 * Get badge variant for a boolean active status
 */
export function getActiveStatusBadgeVariant(
  isActive: boolean
): 'default' | 'outline' {
  return isActive ? 'default' : 'outline'
}

/**
 * Get badge variant for a boolean accessibility status
 */
export function getAccessibilityBadgeVariant(
  isAccessible: boolean
): 'success' | 'destructive' {
  return isAccessible ? 'success' : 'destructive'
}
