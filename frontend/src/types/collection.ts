/**
 * Collection Type Definitions
 *
 * TypeScript interfaces for collection entities and API interactions.
 * These mirror the backend FastAPI endpoints for photo collections.
 */

// ============================================================================
// Core Types
// ============================================================================

export type CollectionType = 'local' | 's3' | 'gcs' | 'smb'
export type CollectionState = 'live' | 'closed' | 'archived'

export interface Collection {
  id: number
  guid: string  // External identifier (col_xxx)
  name: string
  type: CollectionType
  state: CollectionState
  location: string
  connector_id: number | null  // null for LOCAL, required for remote types
  is_accessible: boolean
  accessibility_message: string | null
  cache_ttl: number | null
  created_at: string  // ISO 8601 timestamp
  updated_at: string  // ISO 8601 timestamp
  last_scanned_at: string | null  // ISO 8601 timestamp
}

// ============================================================================
// API Request Types
// ============================================================================

export interface CollectionCreateRequest {
  name: string
  type: CollectionType
  state: CollectionState
  location: string
  connector_id: number | null
  cache_ttl: number | null
}

export interface CollectionUpdateRequest {
  name?: string
  type?: CollectionType
  state?: CollectionState
  location?: string
  connector_id?: number | null
  cache_ttl?: number | null
}

// ============================================================================
// API Query Parameters
// ============================================================================

export interface CollectionListQueryParams {
  state?: CollectionState
  type?: CollectionType
  accessible_only?: boolean
  limit?: number
  offset?: number
}

// ============================================================================
// API Response Types
// ============================================================================

export interface CollectionListResponse {
  collections: Collection[]
  total: number
}

export interface CollectionDetailResponse {
  collection: Collection
}

export interface CollectionTestResponse {
  success: boolean
  is_accessible: boolean
  message: string
  details?: {
    test_time_ms?: number
    file_count?: number
    total_size_bytes?: number
    [key: string]: unknown
  }
}

export interface CollectionDeleteResponse {
  success: boolean
  message: string
}

// ============================================================================
// Form Data Types
// ============================================================================

export interface CollectionFormData {
  name: string
  type: CollectionType
  state: CollectionState
  location: string
  connector_id: number | null
  cache_ttl: number | null
}

export interface CollectionCreate extends Omit<Collection,
  'id' | 'guid' | 'is_accessible' | 'accessibility_message' | 'created_at' | 'updated_at' | 'last_scanned_at'
> {}

export interface CollectionUpdate extends Partial<CollectionCreate> {}
