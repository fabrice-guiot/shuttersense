/**
 * Collection Component Contracts
 *
 * Defines prop interfaces for collection-related components
 */

import type {
  Collection,
  CollectionType,
  CollectionState,
  CollectionFilters
} from '../api/collection-api'
import type { CollectionFormData } from '@/types/schemas/collection'
import type { Connector } from '../api/connector-api'

// ============================================================================
// CollectionList Component
// ============================================================================

export interface CollectionListProps {
  /**
   * List of collections to display
   */
  collections: Collection[]

  /**
   * Loading state (shows skeleton/spinner)
   */
  loading: boolean

  /**
   * Callback when edit button clicked
   */
  onEdit: (collection: Collection) => void

  /**
   * Callback when delete button clicked
   */
  onDelete: (collection: Collection) => void

  /**
   * Callback when refresh/test button clicked
   */
  onRefresh: (collection: Collection) => void

  /**
   * Callback when info button clicked
   */
  onInfo: (collection: Collection) => void

  /**
   * Additional CSS classes
   */
  className?: string
}

// ============================================================================
// CollectionForm Component
// ============================================================================

export interface CollectionFormProps {
  /**
   * Collection to edit (undefined for create mode)
   */
  collection?: Collection

  /**
   * Available connectors for remote collections
   * Used to populate connector dropdown
   */
  connectors: Connector[]

  /**
   * Callback when form is submitted
   * Returns Promise for async operations
   */
  onSubmit: (data: CollectionFormData) => Promise<void>

  /**
   * Callback when cancel button clicked
   */
  onCancel: () => void

  /**
   * Loading state during submission
   */
  loading?: boolean

  /**
   * Error message to display
   */
  error?: string | null

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Form mode determined by presence of collection prop
 */
export type CollectionFormMode = 'create' | 'edit'

// ============================================================================
// CollectionStatus Component
// ============================================================================

export interface CollectionStatusProps {
  /**
   * Collection to display status for
   */
  collection: Collection

  /**
   * Show detailed error message
   * Default: false (only show badge)
   */
  showDetails?: boolean

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Status display configuration
 */
export interface StatusConfig {
  accessible: {
    badgeVariant: 'default'
    dotColor: 'bg-green-400'
    badgeText: 'Accessible'
    backgroundColor: 'bg-green-900/30'
    textColor: 'text-green-400'
  }
  notAccessible: {
    badgeVariant: 'destructive'
    dotColor: 'bg-red-400'
    badgeText: 'Not Accessible'
    backgroundColor: 'bg-red-900/30'
    textColor: 'text-red-400'
  }
}

// ============================================================================
// FiltersSection Component
// ============================================================================

export interface FiltersSectionProps {
  /**
   * Current state filter selection
   */
  selectedState: CollectionState | 'ALL' | ''

  /**
   * Callback when state filter changes
   */
  setSelectedState: (state: CollectionState | 'ALL' | '') => void

  /**
   * Current type filter selection
   */
  selectedType: CollectionType | 'ALL' | ''

  /**
   * Callback when type filter changes
   */
  setSelectedType: (type: CollectionType | 'ALL' | '') => void

  /**
   * Current accessible-only filter state
   */
  accessibleOnly: boolean

  /**
   * Callback when accessible-only filter changes
   */
  setAccessibleOnly: (value: boolean) => void

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * State filter options
 */
export const COLLECTION_STATE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All States' },
  { value: 'live', label: 'Live' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived' }
] as const

/**
 * Type filter options
 */
export const COLLECTION_TYPE_FILTER_OPTIONS = [
  { value: 'ALL', label: 'All Types' },
  { value: 'local', label: 'Local' },
  { value: 's3', label: 'Amazon S3' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'smb', label: 'SMB/CIFS' }
] as const

// ============================================================================
// CollectionTabs Component
// ============================================================================

export interface CollectionTabsProps {
  /**
   * Currently active tab
   */
  activeTab: 'all' | 'recent' | 'archived'

  /**
   * Callback when tab changes
   */
  onTabChange: (tab: 'all' | 'recent' | 'archived') => void

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Tab configuration
 */
export const COLLECTION_TABS = [
  { id: 'all', label: 'All Collections' },
  { id: 'recent', label: 'Recently Accessed' },
  { id: 'archived', label: 'Archived' }
] as const

// ============================================================================
// Type/State Badge Configuration
// ============================================================================

/**
 * Badge variant mapping for collection types
 */
export const COLLECTION_TYPE_BADGE_VARIANT: Record<
  CollectionType,
  'default' | 'secondary'
> = {
  local: 'default',
  s3: 'secondary',
  gcs: 'secondary',
  smb: 'secondary'
}

/**
 * Badge variant mapping for collection states
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
 * Display labels for collection types
 */
export const COLLECTION_TYPE_LABELS: Record<CollectionType, string> = {
  local: 'Local',
  s3: 'Amazon S3',
  gcs: 'Google Cloud Storage',
  smb: 'SMB/CIFS'
}

/**
 * Display labels for collection states
 */
export const COLLECTION_STATE_LABELS: Record<CollectionState, string> = {
  live: 'Live',
  closed: 'Closed',
  archived: 'Archived'
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Filter connectors by type for collection form
 */
export function getConnectorsForType(
  connectors: Connector[],
  collectionType: CollectionType
): Connector[] {
  if (collectionType === 'local') {
    return []
  }

  // Map collection type to connector type
  const connectorType = collectionType // Same naming

  return connectors.filter(
    (connector) => connector.type === connectorType && connector.is_active
  )
}

/**
 * Validate connector selection for collection type
 */
export function isConnectorRequiredForType(type: CollectionType): boolean {
  return type !== 'local'
}

/**
 * Get connector field visibility for collection type
 */
export function shouldShowConnectorField(type: CollectionType): boolean {
  return type !== 'local'
}
