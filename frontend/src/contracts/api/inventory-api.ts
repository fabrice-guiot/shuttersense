/**
 * TypeScript type definitions for Bucket Inventory Import feature
 * Feature: 107-bucket-inventory-import
 */

// ============================================================================
// Inventory Configuration
// ============================================================================

export type InventoryProvider = 's3' | 'gcs'
export type InventoryFormat = 'CSV' | 'ORC' | 'Parquet'
export type InventorySchedule = 'manual' | 'daily' | 'weekly'
export type InventoryValidationStatus = 'pending' | 'validating' | 'validated' | 'failed'

export interface S3InventoryConfig {
  provider: 's3'
  destination_bucket: string
  destination_prefix?: string
  source_bucket: string
  config_name: string
  format: 'CSV' | 'ORC' | 'Parquet'
}

export interface GCSInventoryConfig {
  provider: 'gcs'
  destination_bucket: string
  report_config_name: string
  format: 'CSV' | 'Parquet'
}

export type InventoryConfig = S3InventoryConfig | GCSInventoryConfig

// ============================================================================
// Connector with Inventory
// ============================================================================

export interface ConnectorInventoryFields {
  inventory_config: InventoryConfig | null
  inventory_validation_status: InventoryValidationStatus | null
  inventory_validation_error: string | null
  inventory_last_import_at: string | null
  inventory_schedule: InventorySchedule
}

// ============================================================================
// Inventory Folders
// ============================================================================

export interface InventoryFolder {
  guid: string
  path: string
  object_count: number
  total_size_bytes: number
  deepest_modified: string | null
  discovered_at: string
  collection_guid: string | null
  suggested_name: string | null
}

export interface InventoryFolderList {
  folders: InventoryFolder[]
  total_count: number
  has_more: boolean
}

export interface InventoryFolderQueryParams {
  path_prefix?: string
  unmapped_only?: boolean
  limit?: number
  offset?: number
}

// ============================================================================
// Inventory Status
// ============================================================================

export type ImportPhase = 'folder_extraction' | 'file_info_population' | 'delta_detection'

export interface JobSummary {
  guid: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  phase: ImportPhase | null
  progress_percentage: number
}

export interface InventoryStatus {
  validation_status: InventoryValidationStatus | null
  validation_error: string | null
  last_import_at: string | null
  next_scheduled_at: string | null
  folder_count: number
  mapped_folder_count: number
  current_job: JobSummary | null
}

// ============================================================================
// Collection Creation from Inventory
// ============================================================================

export type CollectionState = 'live' | 'archived' | 'closed'

export interface FolderToCollectionMapping {
  folder_guid: string
  name: string
  state: CollectionState
  pipeline_guid?: string | null
}

export interface CreateCollectionsFromInventoryRequest {
  connector_guid: string
  folders: FolderToCollectionMapping[]
}

export interface CollectionCreatedSummary {
  collection_guid: string
  folder_guid: string
  name: string
}

export interface CollectionCreationError {
  folder_guid: string
  error: string
}

export interface CreateCollectionsFromInventoryResponse {
  created: CollectionCreatedSummary[]
  errors: CollectionCreationError[]
}

// ============================================================================
// FileInfo
// ============================================================================

export interface FileInfo {
  key: string
  size: number
  last_modified: string
  etag?: string | null
  storage_class?: string | null
}

export type FileInfoSource = 'api' | 'inventory'

export interface FileInfoSummary {
  count: number
  source: FileInfoSource | null
  updated_at: string | null
  delta: DeltaSummary | null
}

// ============================================================================
// Delta Summary
// ============================================================================

export interface DeltaSummary {
  new_count: number
  modified_count: number
  deleted_count: number
  computed_at?: string
}

// ============================================================================
// UI State Types
// ============================================================================

export interface FolderTreeNode {
  path: string
  name: string
  objectCount: number
  totalSize: number
  children: FolderTreeNode[]
  isExpanded: boolean
  isSelected: boolean
  isMapped: boolean
  isDisabled: boolean
  disabledReason?: string
}

export interface DraftCollection {
  folder_guid: string
  folder_path: string
  name: string
  state: CollectionState
  pipeline_guid: string | null
}

export interface FolderSelectionState {
  selectedPaths: Set<string>
  mappedPaths: Set<string>
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface InventoryConfigRequest {
  config: InventoryConfig
  schedule: InventorySchedule
}

export interface InventoryImportTriggerResponse {
  job_guid: string
  message: string
}

// ============================================================================
// Form Schemas (for react-hook-form + zod)
// ============================================================================

export interface S3InventoryFormData {
  provider: 's3'
  destination_bucket: string
  destination_prefix?: string
  source_bucket: string
  config_name: string
  format: 'CSV' | 'ORC' | 'Parquet'
  schedule: InventorySchedule
}

export interface GCSInventoryFormData {
  provider: 'gcs'
  destination_bucket: string
  report_config_name: string
  format: 'CSV' | 'Parquet'
  schedule: InventorySchedule
}

export type InventoryFormData = S3InventoryFormData | GCSInventoryFormData

export interface CreateCollectionsFormData {
  drafts: DraftCollection[]
  batch_state?: CollectionState
}
