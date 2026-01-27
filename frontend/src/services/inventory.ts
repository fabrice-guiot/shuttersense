/**
 * Inventory API service
 *
 * Handles all API calls related to cloud storage bucket inventory configuration,
 * validation, and folder management.
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  InventoryConfig,
  InventorySchedule,
  InventoryStatus,
  InventoryFolder,
  InventoryFolderList,
  InventoryFolderQueryParams
} from '@/contracts/api/inventory-api'

// ============================================================================
// Request/Response Types
// ============================================================================

export interface SetInventoryConfigRequest {
  config: InventoryConfig
  schedule: InventorySchedule
}

export interface SetInventoryConfigResponse {
  message: string
  validation_status: string
  job_guid?: string
}

// ============================================================================
// Inventory Configuration API
// ============================================================================

/**
 * Set inventory configuration on a connector
 * @param connectorGuid - Connector GUID (con_xxx format)
 * @param request - Inventory configuration and schedule
 */
export const setInventoryConfig = async (
  connectorGuid: string,
  request: SetInventoryConfigRequest
): Promise<SetInventoryConfigResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))
  const response = await api.put<SetInventoryConfigResponse>(
    `/connectors/${safeGuid}/inventory/config`,
    request
  )
  return response.data
}

/**
 * Clear inventory configuration from a connector
 * @param connectorGuid - Connector GUID (con_xxx format)
 */
export const clearInventoryConfig = async (connectorGuid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))
  await api.delete(`/connectors/${safeGuid}/inventory/config`)
}

/**
 * Get inventory status for a connector
 * @param connectorGuid - Connector GUID (con_xxx format)
 */
export const getInventoryStatus = async (connectorGuid: string): Promise<InventoryStatus> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))
  const response = await api.get<InventoryStatus>(`/connectors/${safeGuid}/inventory/status`)
  return response.data
}

// ============================================================================
// Inventory Folders API
// ============================================================================

/**
 * List inventory folders for a connector
 * @param connectorGuid - Connector GUID (con_xxx format)
 * @param params - Query parameters for filtering and pagination
 */
export const listInventoryFolders = async (
  connectorGuid: string,
  params: InventoryFolderQueryParams = {}
): Promise<InventoryFolderList> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))

  const queryParams: Record<string, string | number | boolean> = {}
  if (params.path_prefix) queryParams.path_prefix = params.path_prefix
  if (params.unmapped_only) queryParams.unmapped_only = true
  if (params.limit) queryParams.limit = params.limit
  if (params.offset) queryParams.offset = params.offset

  const response = await api.get<InventoryFolderList>(
    `/connectors/${safeGuid}/inventory/folders`,
    { params: queryParams }
  )
  return response.data
}

/**
 * Get a single inventory folder by GUID
 * @param folderGuid - Folder GUID (fld_xxx format)
 */
export const getInventoryFolder = async (folderGuid: string): Promise<InventoryFolder> => {
  const safeGuid = encodeURIComponent(validateGuid(folderGuid, 'fld'))
  const response = await api.get<InventoryFolder>(`/inventory/folders/${safeGuid}`)
  return response.data
}

// ============================================================================
// Inventory Validation API
// ============================================================================

export interface ValidateInventoryResponse {
  success: boolean
  message: string
  validation_status: string
  job_guid?: string | null
}

/**
 * Validate inventory configuration by checking manifest.json accessibility
 * @param connectorGuid - Connector GUID (con_xxx format)
 */
export const validateInventoryConfig = async (
  connectorGuid: string
): Promise<ValidateInventoryResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))
  const response = await api.post<ValidateInventoryResponse>(
    `/connectors/${safeGuid}/inventory/validate`
  )
  return response.data
}

// ============================================================================
// Inventory Import API
// ============================================================================

export interface TriggerImportResponse {
  job_guid: string
  message: string
}

/**
 * Trigger inventory import for a connector
 * @param connectorGuid - Connector GUID (con_xxx format)
 */
export const triggerInventoryImport = async (
  connectorGuid: string
): Promise<TriggerImportResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(connectorGuid, 'con'))
  const response = await api.post<TriggerImportResponse>(
    `/connectors/${safeGuid}/inventory/import`
  )
  return response.data
}

// ============================================================================
// Collection Creation from Inventory API
// ============================================================================

import type {
  FolderToCollectionMapping,
  CreateCollectionsFromInventoryResponse
} from '@/contracts/api/inventory-api'

export interface CreateCollectionsRequest {
  connector_guid: string
  folders: FolderToCollectionMapping[]
}

/**
 * Create collections from inventory folders
 * @param connectorGuid - Connector GUID (con_xxx format)
 * @param folders - List of folder-to-collection mappings
 */
export const createCollectionsFromInventory = async (
  connectorGuid: string,
  folders: FolderToCollectionMapping[]
): Promise<CreateCollectionsFromInventoryResponse> => {
  // Validate connector GUID format
  validateGuid(connectorGuid, 'con')

  const response = await api.post<CreateCollectionsFromInventoryResponse>(
    '/collections/from-inventory',
    {
      connector_guid: connectorGuid,
      folders
    }
  )
  return response.data
}
